from __future__ import annotations

import asyncio
import heapq
import time
from collections import defaultdict

from loguru import logger

from .message import Message


class InMemoryQueue:
    """Dict-backed queue for local development and testing.

    Messages are stored in a list per queue.  Delayed messages use a
    min-heap ordered by ``scheduled_at``.  All synchronisation is via
    :class:`asyncio.Lock` — only works within a single process.
    """

    def __init__(self) -> None:
        self._queues: dict[str, list[tuple[str, Message]]] = defaultdict(list)
        self._delayed: dict[str, list[tuple[float, str, Message]]] = defaultdict(
            list
        )
        self._dead: dict[str, list[Message]] = defaultdict(list)
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._events: dict[str, asyncio.Event] = defaultdict(asyncio.Event)
        self._entry_counter: int = 0
        self._closed: bool = False

    def _next_entry_id(self) -> str:
        self._entry_counter += 1
        return f"mem-{self._entry_counter}"

    def _lock(self, queue_name: str) -> asyncio.Lock:
        return self._locks[queue_name]

    def _event(self, queue_name: str) -> asyncio.Event:
        return self._events[queue_name]

    # -- QueueBackend --------------------------------------------------------

    async def publish(self, queue_name: str, message: Message) -> str:
        async with self._lock(queue_name):
            if message.is_scheduled:
                heapq.heappush(
                    self._delayed[queue_name],
                    (message.scheduled_at, message.message_id, message),
                )
                return message.message_id

            entry_id = self._next_entry_id()
            self._queues[queue_name].append((entry_id, message))
            self._event(queue_name).set()
            return entry_id

    async def publish_batch(
        self, queue_name: str, messages: list[Message]
    ) -> list[str]:
        return [await self.publish(queue_name, msg) for msg in messages]

    async def consume(
        self,
        queue_name: str,
        consumer_name: str,
        *,
        batch_size: int = 10,
        poll_timeout_ms: int = 5000,
    ) -> list[tuple[str, Message]]:
        await self._promote_due(queue_name)

        async with self._lock(queue_name):
            batch = self._queues[queue_name][:batch_size]
            if batch:
                return list(batch)

        # Wait for new messages up to poll_timeout.
        event = self._event(queue_name)
        event.clear()
        try:
            await asyncio.wait_for(
                event.wait(), timeout=poll_timeout_ms / 1000.0
            )
        except asyncio.TimeoutError:
            return []

        async with self._lock(queue_name):
            return list(self._queues[queue_name][:batch_size])

    async def ack(
        self, queue_name: str, consumer_name: str, entry_id: str
    ) -> None:
        async with self._lock(queue_name):
            self._queues[queue_name] = [
                (eid, msg)
                for eid, msg in self._queues[queue_name]
                if eid != entry_id
            ]

    async def nack(
        self,
        queue_name: str,
        consumer_name: str,
        entry_id: str,
        *,
        requeue: bool = True,
    ) -> None:
        msg: Message | None = None
        async with self._lock(queue_name):
            remaining: list[tuple[str, Message]] = []
            for eid, m in self._queues[queue_name]:
                if eid == entry_id:
                    msg = m
                else:
                    remaining.append((eid, m))
            self._queues[queue_name] = remaining

        if msg is None:
            return

        if requeue and msg.retry_count < msg.max_retries:
            msg.retry_count += 1
            msg.scheduled_at = time.time() + msg.next_retry_delay()
            await self.publish(queue_name, msg)
        else:
            self._dead[queue_name].append(msg)
            logger.warning(
                "Dead-lettered {} on {}", msg.message_id, queue_name
            )

    async def queue_length(self, queue_name: str) -> int:
        return len(self._queues.get(queue_name, []))

    async def purge(self, queue_name: str) -> int:
        async with self._lock(queue_name):
            length = len(self._queues[queue_name])
            self._queues[queue_name] = []
            self._delayed[queue_name] = []
            return length

    async def close(self) -> None:
        self._closed = True

    # -- helpers -------------------------------------------------------------

    async def _promote_due(self, queue_name: str) -> int:
        """Move due delayed messages into the ready queue."""
        async with self._lock(queue_name):
            now = time.time()
            promoted = 0
            while (
                self._delayed[queue_name]
                and self._delayed[queue_name][0][0] <= now
            ):
                _, _, msg = heapq.heappop(self._delayed[queue_name])
                msg.scheduled_at = None
                entry_id = self._next_entry_id()
                self._queues[queue_name].append((entry_id, msg))
                promoted += 1
            if promoted:
                self._event(queue_name).set()
        return promoted
