from __future__ import annotations

import json
import time
from typing import Any

from loguru import logger

from .config import QueueSettings
from .message import Message


class RedisStreamsQueue:
    """Redis Streams–backed queue with consumer groups, delayed delivery,
    retry with exponential back-off, and dead-letter support.

    Redis key layout::

        {queue_name}:stream   — main delivery stream
        {queue_name}:delayed  — sorted set for scheduled messages
        {queue_name}:dead     — dead-letter stream

    If no *redis* client is provided the global client from
    :func:`alkit_infra.redis.client.get_redis` is used (lazy import).
    """

    def __init__(
        self,
        redis: Any | None = None,
        settings: QueueSettings | None = None,
    ) -> None:
        self._settings = settings or QueueSettings()
        if redis is not None:
            self._redis = redis
        else:
            from alkit_infra.redis.client import get_redis

            self._redis = get_redis()
        self._groups_created: set[str] = set()

    # -- key helpers ---------------------------------------------------------

    @staticmethod
    def _stream_key(queue_name: str) -> str:
        return f"{queue_name}:stream"

    @staticmethod
    def _delayed_key(queue_name: str) -> str:
        return f"{queue_name}:delayed"

    @staticmethod
    def _dead_key(queue_name: str) -> str:
        return f"{queue_name}:dead"

    @staticmethod
    def _group_name(queue_name: str) -> str:
        return f"cg:{queue_name}"

    # -- consumer group management -------------------------------------------

    async def _ensure_group(self, queue_name: str) -> None:
        group = self._group_name(queue_name)
        if group in self._groups_created:
            return
        stream = self._stream_key(queue_name)
        try:
            await self._redis.xgroup_create(stream, group, id="0", mkstream=True)
            logger.debug("Created consumer group {} on {}", group, stream)
        except Exception:
            # BUSYGROUP = already exists; safe to ignore.
            pass
        self._groups_created.add(group)

    # -- QueueBackend --------------------------------------------------------

    async def publish(self, queue_name: str, message: Message) -> str:
        await self._ensure_group(queue_name)
        fields = message.to_dict()

        if message.is_scheduled:
            member = json.dumps(fields, ensure_ascii=False)
            await self._redis.zadd(
                self._delayed_key(queue_name),
                {member: message.scheduled_at},
            )
            logger.debug(
                "Scheduled message {} for {} (deliver at {:.0f})",
                message.message_id,
                queue_name,
                message.scheduled_at,
            )
            return message.message_id

        entry_id: str = await self._redis.xadd(
            self._stream_key(queue_name), fields
        )
        await self._redis.xtrim(
            self._stream_key(queue_name),
            maxlen=self._settings.default_max_length,
            approximate=True,
        )
        logger.debug(
            "Published {} to {} [entry={}]",
            message.message_id,
            queue_name,
            entry_id,
        )
        return entry_id

    async def publish_batch(
        self, queue_name: str, messages: list[Message]
    ) -> list[str]:
        if not messages:
            return []

        results: list[str] = []
        async with self._redis.pipeline() as pipe:
            for msg in messages:
                fields = msg.to_dict()
                if msg.is_scheduled:
                    member = json.dumps(fields, ensure_ascii=False)
                    pipe.zadd(
                        self._delayed_key(queue_name),
                        {member: msg.scheduled_at},
                    )
                    results.append(msg.message_id)
                else:
                    pipe.xadd(self._stream_key(queue_name), fields)
                    results.append("")  # placeholder; replaced below
            raw = await pipe.execute()

        await self._ensure_group(queue_name)

        # Replace XADD placeholders with actual entry IDs.
        pipe_idx = 0
        for i, msg in enumerate(messages):
            if not msg.is_scheduled:
                results[i] = str(raw[pipe_idx])
            pipe_idx += 1
        return results

    async def consume(
        self,
        queue_name: str,
        consumer_name: str,
        *,
        batch_size: int = 10,
        poll_timeout_ms: int = 5000,
    ) -> list[tuple[str, Message]]:
        await self._ensure_group(queue_name)
        group = self._group_name(queue_name)
        stream = self._stream_key(queue_name)

        # Try to reclaim messages stuck in crashed consumers.
        await self._claim_stuck(queue_name, consumer_name)

        result = await self._redis.xreadgroup(
            group,
            consumer_name,
            {stream: ">"},
            count=batch_size,
            block=poll_timeout_ms,
        )
        if not result:
            return []

        # result: [(stream_name, [(entry_id, field_dict), ...])]
        messages: list[tuple[str, Message]] = []
        for _stream_name, entries in result:
            for entry_id, fields in entries:
                msg = Message.from_dict(fields, entry_id=entry_id)
                messages.append((entry_id, msg))
        return messages

    async def ack(
        self, queue_name: str, consumer_name: str, entry_id: str
    ) -> None:
        await self._redis.xack(
            self._stream_key(queue_name),
            self._group_name(queue_name),
            entry_id,
        )

    async def nack(
        self,
        queue_name: str,
        consumer_name: str,
        entry_id: str,
        *,
        requeue: bool = True,
    ) -> None:
        # Retrieve the message fields before ack-ing.
        entries = await self._redis.xrange(
            self._stream_key(queue_name), entry_id, entry_id, count=1
        )
        if not entries:
            return

        _, fields = entries[0]
        msg = Message.from_dict(fields, entry_id=entry_id)

        # ACK to remove from the pending list.
        await self.ack(queue_name, consumer_name, entry_id)

        if requeue and msg.retry_count < msg.max_retries:
            msg.retry_count += 1
            msg.scheduled_at = time.time() + msg.next_retry_delay()
            await self.publish(queue_name, msg)
        else:
            # Dead-letter.
            await self._redis.xadd(self._dead_key(queue_name), msg.to_dict())
            logger.warning(
                "Dead-lettered message {} on {} after {} retries",
                msg.message_id,
                queue_name,
                msg.retry_count,
            )

    async def queue_length(self, queue_name: str) -> int:
        try:
            info = await self._redis.xinfo_stream(self._stream_key(queue_name))
            return info.get("length", 0)
        except Exception:
            return 0

    async def purge(self, queue_name: str) -> int:
        stream = self._stream_key(queue_name)
        try:
            info = await self._redis.xinfo_stream(stream)
            length = info.get("length", 0)
        except Exception:
            length = 0
        await self._redis.delete(stream, self._delayed_key(queue_name))
        return length

    async def close(self) -> None:
        """No-op — the Redis client lifecycle is managed by ``alkit_infra.redis.client``."""

    # -- delayed message scheduler -------------------------------------------

    async def promote_due_messages(self, queue_name: str) -> int:
        """Move all due delayed messages into the delivery stream.

        Called periodically by the :class:`QueueConsumer` scheduler loop.
        Returns the number of messages promoted.
        """
        delayed_key = self._delayed_key(queue_name)
        now = time.time()

        due = await self._redis.zrangebyscore(
            delayed_key, "-inf", now, withscores=True
        )
        if not due:
            return 0

        promoted = 0
        for member, _score in due:
            if isinstance(member, bytes):
                member = member.decode()
            fields = json.loads(member)
            msg = Message.from_dict(fields)
            msg.scheduled_at = None
            await self._redis.xadd(self._stream_key(queue_name), msg.to_dict())
            await self._redis.zrem(delayed_key, member)
            promoted += 1

        if promoted:
            logger.debug(
                "Promoted {} delayed messages for {}", promoted, queue_name
            )
        return promoted

    # -- stuck message recovery ----------------------------------------------

    async def _claim_stuck(self, queue_name: str, consumer_name: str) -> int:
        """Claim pending messages idle longer than ``claim_min_idle_ms``."""
        group = self._group_name(queue_name)
        stream = self._stream_key(queue_name)

        try:
            pending = await self._redis.xpending_range(
                stream,
                group,
                min="-",
                max="+",
                count=10,
                idle=self._settings.claim_min_idle_ms,
            )
        except Exception:
            return 0

        if not pending:
            return 0

        entry_ids = [p["message_id"] for p in pending]
        try:
            await self._redis.xclaim(
                stream, group, consumer_name,
                self._settings.claim_min_idle_ms, entry_ids,
            )
            logger.debug(
                "Claimed {} stuck messages from {}", len(entry_ids), queue_name
            )
            return len(entry_ids)
        except Exception:
            logger.opt(exception=True).debug(
                "Failed to claim stuck messages on {}", queue_name
            )
            return 0
