from __future__ import annotations

import asyncio
import logging
import random
import threading
from dataclasses import dataclass
from typing import Any

from alkit_infra.queue import Message

from .config import ObservabilitySettings
from .contracts import TRACE_QUEUE_NAME, TraceEnvelope

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PublisherStats:
    published: int = 0
    retried: int = 0
    dropped: int = 0
    queue_depth: int = 0


class AsyncTracePublisher:
    """Bounded, non-blocking bridge from synchronous SpanProcessor to Redis."""

    def __init__(self, queue_backend: Any | None, settings: ObservabilitySettings) -> None:
        self._backend = queue_backend
        self._settings = settings
        self._queue: asyncio.Queue[TraceEnvelope] = asyncio.Queue(
            maxsize=settings.publisher_queue_capacity,
        )
        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._slots = threading.BoundedSemaphore(
            settings.publisher_queue_capacity,
        )
        self.stats = PublisherStats()

    async def start(self) -> None:
        if self._running or self._backend is None:
            return
        self._loop = asyncio.get_running_loop()
        self._running = True
        self._task = asyncio.create_task(self._run(), name="observability-trace-publisher")

    def submit_nowait(self, envelope: TraceEnvelope) -> bool:
        if not self._running or self._loop is None:
            self.stats.dropped += 1
            return False
        if not self._slots.acquire(blocking=False):
            self.stats.dropped += 1
            logger.warning("trace_publisher.queue_full trace_id=%s", envelope.trace_id)
            return False

        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop is self._loop:
            return self._enqueue_reserved(envelope)
        try:
            self._loop.call_soon_threadsafe(self._enqueue_reserved, envelope)
            return True
        except RuntimeError:
            self._slots.release()
            self.stats.dropped += 1
            return False

    async def shutdown(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._task is not None:
            try:
                await asyncio.wait_for(
                    asyncio.shield(self._task),
                    timeout=self._settings.flush_timeout_seconds,
                )
            except asyncio.TimeoutError:
                pending = self._queue.qsize()
                self.stats.dropped += pending
                logger.warning("trace_publisher.flush_timeout pending=%d", pending)
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
        self.stats.queue_depth = self._queue.qsize()

    def snapshot(self) -> dict[str, int]:
        self.stats.queue_depth = self._queue.qsize()
        return {
            "published": self.stats.published,
            "retried": self.stats.retried,
            "dropped": self.stats.dropped,
            "queue_depth": self.stats.queue_depth,
        }

    def _enqueue_reserved(self, envelope: TraceEnvelope) -> bool:
        try:
            self._queue.put_nowait(envelope)
            self.stats.queue_depth = self._queue.qsize()
            return True
        except asyncio.QueueFull:
            self._slots.release()
            self.stats.dropped += 1
            logger.warning("trace_publisher.queue_full trace_id=%s", envelope.trace_id)
            return False

    async def _run(self) -> None:
        interval = self._settings.publish_interval_ms / 1000
        while self._running or not self._queue.empty():
            batch: list[TraceEnvelope] = []
            try:
                first = await asyncio.wait_for(self._queue.get(), timeout=interval)
                batch.append(first)
            except asyncio.TimeoutError:
                if not self._running:
                    break
                continue

            deadline = asyncio.get_running_loop().time() + interval
            while len(batch) < self._settings.publish_batch_size:
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    break
                try:
                    batch.append(
                        await asyncio.wait_for(
                            self._queue.get(),
                            timeout=remaining,
                        ),
                    )
                except asyncio.TimeoutError:
                    break

            try:
                await self._publish(batch)
            except asyncio.CancelledError:
                self.stats.dropped += len(batch)
                raise
            finally:
                for _ in batch:
                    self._queue.task_done()
                    self._slots.release()
            self.stats.queue_depth = self._queue.qsize()

    async def _publish(self, envelopes: list[TraceEnvelope]) -> None:
        messages = [
            Message(
                topic=TRACE_QUEUE_NAME,
                payload=envelope.model_dump_json(),
                max_retries=self._settings.publish_max_retries,
            )
            for envelope in envelopes
        ]
        for attempt in range(self._settings.publish_max_retries + 1):
            try:
                await self._backend.publish_batch(TRACE_QUEUE_NAME, messages)
                self.stats.published += len(messages)
                return
            except asyncio.CancelledError:
                raise
            except Exception:
                if attempt >= self._settings.publish_max_retries:
                    self.stats.dropped += len(messages)
                    logger.exception(
                        "trace_publisher.publish_failed count=%d attempts=%d",
                        len(messages),
                        attempt + 1,
                    )
                    return
                self.stats.retried += len(messages)
                await asyncio.sleep(min(0.05 * (2**attempt), 1.0) * random.uniform(0.5, 1.0))


__all__ = ["AsyncTracePublisher", "PublisherStats"]
