from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine

from loguru import logger

from .config import QueueSettings
from .message import Message

# Type alias for message handler callbacks.
MessageHandler = Callable[[Message], Coroutine[Any, Any, None]]


class QueueConsumer:
    """Consumes messages from a queue and dispatches them to a handler.

    Usage::

        backend = RedisStreamsQueue()
        consumer = QueueConsumer(
            backend=backend,
            queue_name="doc-processing",
            consumer_name="worker-1",
            handler=process_document,
            concurrency=3,
        )
        await consumer.start()
        # ... later ...
        await consumer.stop()

    The consumer runs two background tasks:

    1. **Main loop** — polls the backend with ``consume()``, dispatches
       each message to *handler* under an :class:`asyncio.Semaphore`,
       and calls ``ack`` / ``nack`` accordingly.
    2. **Scheduler loop** — periodically promotes due delayed messages
       (only for backends that implement ``promote_due_messages``).
    """

    def __init__(
        self,
        backend: Any,
        queue_name: str,
        consumer_name: str,
        handler: MessageHandler,
        *,
        concurrency: int = 1,
        settings: QueueSettings | None = None,
    ) -> None:
        self._backend = backend
        self._queue_name = queue_name
        self._consumer_name = consumer_name
        self._handler = handler
        self._concurrency = concurrency
        self._settings = settings or QueueSettings()
        self._semaphore = asyncio.Semaphore(concurrency)
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._scheduler_task: asyncio.Task[None] | None = None

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        """Start consuming messages in background tasks."""
        if self._running:
            logger.warning("Consumer {} already running", self._consumer_name)
            return
        self._running = True
        self._task = asyncio.create_task(
            self._run_loop(), name=f"consumer:{self._consumer_name}"
        )
        self._scheduler_task = asyncio.create_task(
            self._scheduler_loop(),
            name=f"scheduler:{self._consumer_name}",
        )
        logger.info(
            "Consumer {} started on {} (concurrency={})",
            self._consumer_name,
            self._queue_name,
            self._concurrency,
        )

    async def stop(self, timeout: float = 30.0) -> None:
        """Gracefully stop the consumer.

        Waits up to *timeout* seconds for in-flight messages to finish.
        """
        if not self._running:
            return
        self._running = False

        if self._scheduler_task is not None:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        if self._task is not None:
            try:
                await asyncio.wait_for(asyncio.shield(self._task), timeout=timeout)
            except asyncio.TimeoutError:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass

        logger.info("Consumer {} stopped", self._consumer_name)

    # -- internal ------------------------------------------------------------

    async def _run_loop(self) -> None:
        """Main consumption loop."""
        while self._running:
            try:
                batch = await self._backend.consume(
                    self._queue_name,
                    self._consumer_name,
                    batch_size=self._settings.consumer_batch_size,
                    poll_timeout_ms=self._settings.consumer_poll_timeout_ms,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.opt(exception=True).error(
                    "Error reading from {}", self._queue_name
                )
                await asyncio.sleep(1.0)
                continue

            for entry_id, message in batch:
                async with self._semaphore:
                    await self._process_message(entry_id, message)

    async def _process_message(self, entry_id: str, message: Message) -> None:
        """Process a single message — ack on success, nack on failure."""
        try:
            await self._handler(message)
            await self._backend.ack(
                self._queue_name, self._consumer_name, entry_id
            )
            logger.debug(
                "Processed message {} successfully", message.message_id
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.opt(exception=True).warning(
                "Handler failed for message {} on {}: {}",
                message.message_id,
                self._queue_name,
                exc,
            )
            try:
                await self._backend.nack(
                    self._queue_name,
                    self._consumer_name,
                    entry_id,
                    requeue=True,
                )
            except Exception:
                logger.opt(exception=True).error(
                    "Failed to nack message {}", message.message_id
                )

    async def _scheduler_loop(self) -> None:
        """Periodically promote due delayed messages.

        Only active for backends that expose
        ``promote_due_messages()`` (e.g. :class:`RedisStreamsQueue`).
        """
        promote = getattr(self._backend, "promote_due_messages", None)
        if promote is None:
            return

        interval = self._settings.scheduler_poll_interval_seconds
        while self._running:
            try:
                await promote(self._queue_name)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.opt(exception=True).debug(
                    "Scheduler error on {}", self._queue_name
                )
            await asyncio.sleep(interval)
