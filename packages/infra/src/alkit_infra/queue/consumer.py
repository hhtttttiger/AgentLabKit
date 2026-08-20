from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine

from loguru import logger

from .config import QueueSettings
from .message import Message

MessageHandler = Callable[[Message], Coroutine[Any, Any, None]]


class QueueConsumer:
    """Bounded concurrent queue consumer with retry and graceful draining."""

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
        if concurrency < 1:
            raise ValueError("concurrency must be at least 1")
        self._backend = backend
        self._queue_name = queue_name
        self._consumer_name = consumer_name
        self._handler = handler
        self._concurrency = concurrency
        self._settings = settings or QueueSettings()
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._scheduler_task: asyncio.Task[None] | None = None
        self._inflight: set[asyncio.Task[None]] = set()
        self._processed_count = 0
        self._failed_count = 0

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def inflight_count(self) -> int:
        return len(self._inflight)

    @property
    def processed_count(self) -> int:
        return self._processed_count

    @property
    def failed_count(self) -> int:
        return self._failed_count

    async def start(self) -> None:
        if self._running:
            logger.warning("Consumer {} already running", self._consumer_name)
            return
        self._running = True
        self._task = asyncio.create_task(
            self._run_loop(),
            name=f"consumer:{self._consumer_name}",
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

    async def wait(self) -> None:
        if self._task is not None:
            # Supervisors cancel watcher coroutines during coordinated
            # shutdown; shielding prevents that from cancelling the consumer
            # before its explicit stop/drain phase.
            await asyncio.shield(self._task)

    async def stop(self, timeout: float = 30.0) -> None:
        if not self._running and not self._inflight:
            return
        self._running = False
        if self._scheduler_task is not None:
            self._scheduler_task.cancel()
            await _ignore_cancelled(self._scheduler_task)

        async def _drain() -> None:
            try:
                if self._task is not None:
                    await self._task
            finally:
                if self._inflight:
                    await asyncio.gather(
                        *tuple(self._inflight),
                        return_exceptions=True,
                    )

        try:
            await asyncio.wait_for(_drain(), timeout=timeout)
        except asyncio.TimeoutError:
            if self._task is not None:
                self._task.cancel()
            for task in tuple(self._inflight):
                task.cancel()
            await asyncio.gather(
                *(tuple(self._inflight) + ((self._task,) if self._task else ())),
                return_exceptions=True,
            )
        logger.info("Consumer {} stopped", self._consumer_name)

    async def _run_loop(self) -> None:
        consecutive_read_failures = 0
        while self._running:
            self._reap_finished()
            available = self._concurrency - len(self._inflight)
            if available <= 0:
                await asyncio.wait(self._inflight, return_when=asyncio.FIRST_COMPLETED)
                continue

            try:
                batch = await self._backend.consume(
                    self._queue_name,
                    self._consumer_name,
                    batch_size=min(self._settings.consumer_batch_size, available),
                    poll_timeout_ms=self._settings.consumer_poll_timeout_ms,
                )
                consecutive_read_failures = 0
            except asyncio.CancelledError:
                raise
            except Exception:
                consecutive_read_failures += 1
                logger.opt(exception=True).error("Error reading from {}", self._queue_name)
                if consecutive_read_failures >= 5:
                    raise RuntimeError(
                        f"Queue {self._queue_name} failed 5 consecutive reads",
                    )
                await asyncio.sleep(1.0)
                continue

            for entry_id, message in batch[:available]:
                task = asyncio.create_task(
                    self._process_message(entry_id, message),
                    name=f"message:{self._consumer_name}:{entry_id}",
                )
                self._inflight.add(task)

        if self._inflight:
            await asyncio.gather(*tuple(self._inflight), return_exceptions=True)
            self._reap_finished()

    def _reap_finished(self) -> None:
        finished = {task for task in self._inflight if task.done()}
        self._inflight.difference_update(finished)
        for task in finished:
            try:
                task.result()
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.opt(exception=True).error(
                    "Unexpected consumer task failure on {}",
                    self._queue_name,
                )

    async def _process_message(self, entry_id: str, message: Message) -> None:
        try:
            await self._handler(message)
            await self._backend.ack(self._queue_name, self._consumer_name, entry_id)
            self._processed_count += 1
            logger.debug("Processed message {} successfully", message.message_id)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._failed_count += 1
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
                    requeue=not bool(getattr(exc, "non_retryable", False)),
                )
            except Exception:
                logger.opt(exception=True).error("Failed to nack message {}", message.message_id)

    async def _scheduler_loop(self) -> None:
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
                logger.opt(exception=True).debug("Scheduler error on {}", self._queue_name)
            await asyncio.sleep(interval)


async def _ignore_cancelled(task: asyncio.Task[Any]) -> None:
    try:
        await task
    except asyncio.CancelledError:
        pass


__all__ = ["MessageHandler", "QueueConsumer"]
