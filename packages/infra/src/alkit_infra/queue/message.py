from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field


@dataclass(slots=True)
class Message:
    """A queue message.

    The ``payload`` is always a string — callers that need structured data
    should serialise / deserialise externally (e.g. via ``json.dumps`` /
    ``json.loads``), matching the convention of :class:`CacheBackend`.
    """

    topic: str
    payload: str
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: float = field(default_factory=time.time)
    scheduled_at: float | None = None
    retry_count: int = 0
    max_retries: int = 3

    # Populated on receive; empty on publish.
    _entry_id: str | None = field(default=None, repr=False)

    # -- helpers -------------------------------------------------------------

    @property
    def is_scheduled(self) -> bool:
        """True if this message should be delivered in the future."""
        return self.scheduled_at is not None and self.scheduled_at > time.time()

    def remaining_retries(self) -> int:
        return max(0, self.max_retries - self.retry_count)

    def next_retry_delay(self) -> float:
        """Exponential backoff: 5 s * 2^retry_count, capped at 60 s.

        Jitter (uniform 50%-100%) is applied to avoid thundering-herd
        effects when multiple consumers retry simultaneously.
        """
        base = min(5.0 * (2 ** self.retry_count), 60.0)
        return base * random.uniform(0.5, 1.0)

    # -- serialisation -------------------------------------------------------

    def to_dict(self) -> dict[str, str]:
        """Serialise to a flat ``str → str`` dict for Redis XADD / ZADD."""
        d: dict[str, str] = {
            "topic": self.topic,
            "payload": self.payload,
            "message_id": self.message_id,
            "created_at": str(self.created_at),
            "retry_count": str(self.retry_count),
            "max_retries": str(self.max_retries),
        }
        if self.scheduled_at is not None:
            d["scheduled_at"] = str(self.scheduled_at)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, str], entry_id: str | None = None) -> Message:
        """Deserialise from a flat ``str → str`` dict."""
        return cls(
            topic=data["topic"],
            payload=data["payload"],
            message_id=data.get("message_id", uuid.uuid4().hex),
            created_at=float(data.get("created_at", "0") or "0") or time.time(),
            scheduled_at=float(data["scheduled_at"]) if "scheduled_at" in data else None,
            retry_count=int(data.get("retry_count", "0")),
            max_retries=int(data.get("max_retries", "3")),
            _entry_id=entry_id,
        )
