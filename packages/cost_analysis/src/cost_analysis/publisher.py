"""CostPublisher — 将 CostRecord 发布到队列。

用于 CostProjector 将成本记录发布到 Redis 队列，
供 worker 异步写入 PostgreSQL。
"""

from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass
from typing import Any

from .contracts import CostRecord

logger = logging.getLogger(__name__)

COST_QUEUE_NAME = "cost_records"


@dataclass(slots=True)
class PublisherStats:
    published: int = 0
    dropped: int = 0
    queue_depth: int = 0


class CostPublisher:
    """Bounded, non-blocking bridge from CostProjector to Redis queue."""

    def __init__(
        self,
        queue_backend: Any | None,
        queue_capacity: int = 1024,
    ) -> None:
        self._backend = queue_backend
        self._queue: asyncio.Queue[CostRecord] = asyncio.Queue(
            maxsize=queue_capacity,
        )
        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._slots = threading.BoundedSemaphore(queue_capacity)
        self.stats = PublisherStats()

    async def start(self) -> None:
        if self._running or self._backend is None:
            return
        self._loop = asyncio.get_running_loop()
        self._running = True
        self._task = asyncio.create_task(self._run(), name="cost-publisher")

    def submit_nowait(self, record: CostRecord) -> bool:
        if not self._running or self._loop is None:
            self.stats.dropped += 1
            return False
        if not self._slots.acquire(blocking=False):
            self.stats.dropped += 1
            logger.warning("cost_publisher.queue_full run_id=%s", record.run_id)
            return False

        try:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, record)
            self.stats.published += 1
            return True
        except (RuntimeError, asyncio.QueueFull):
            self._slots.release()
            self.stats.dropped += 1
            return False

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self) -> None:
        buffer: list[CostRecord] = []

        while self._running:
            try:
                record = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0
                )
                buffer.append(record)
                self._slots.release()

                # Drain up to 63 more without blocking
                for _ in range(63):
                    try:
                        buffer.append(self._queue.get_nowait())
                        self._slots.release()
                    except asyncio.QueueEmpty:
                        break

                if self._backend is not None:
                    try:
                        payload = _serialize_batch(buffer)
                        await self._backend.enqueue(
                            COST_QUEUE_NAME,
                            payload,
                        )
                    except Exception:
                        logger.exception(
                            "cost_publisher.enqueue_error count=%d",
                            len(buffer),
                        )

                buffer.clear()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break


def _serialize_batch(records: list[CostRecord]) -> list[dict[str, Any]]:
    """将 CostRecord 列表序列化为可 JSON 化的字典。"""
    return [
        {
            "run_id": r.run_id,
            "trace_id": r.trace_id,
            "span_id": r.span_id,
            "agent_key": r.agent_key,
            "model": r.model,
            "provider": r.provider,
            "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens,
            "cache_write_tokens": r.cache_write_tokens,
            "cache_read_tokens": r.cache_read_tokens,
            "estimated_cost": r.estimated_cost,
            "started_at_utc": r.started_at_utc.isoformat(),
            "completed_at_utc": r.completed_at_utc.isoformat(),
            "error_code": r.error_code,
            "error_message": r.error_message,
        }
        for r in records
    ]


__all__ = ["CostPublisher", "COST_QUEUE_NAME", "PublisherStats"]
