from __future__ import annotations

import asyncio
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from ..contracts.models import AgentMessage


@dataclass(slots=True)
class SessionSnapshot:
    session_id: str
    messages: list[AgentMessage] = field(default_factory=list)
    summary: str | None = None
    turn_count: int = 0
    total_tokens_consumed: int = 0
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def clone(self) -> "SessionSnapshot":
        return SessionSnapshot(
            session_id=self.session_id,
            messages=[message.model_copy(deep=True) for message in self.messages],
            summary=self.summary,
            turn_count=self.turn_count,
            total_tokens_consumed=self.total_tokens_consumed,
            updated_at=self.updated_at,
        )


class SessionStore(Protocol):
    async def load(self, session_id: str) -> SessionSnapshot | None:
        ...

    async def save(self, session_id: str, snapshot: SessionSnapshot) -> None:
        ...

    async def delete(self, session_id: str) -> None:
        ...


class InMemorySessionStore:
    """In-process session store with optional LRU eviction.

    Intended for development and testing. For production workloads use a
    persistent store such as ``PostgresSessionStore``.
    """

    def __init__(self, max_sessions: int = 1024) -> None:
        self._items: OrderedDict[str, SessionSnapshot] = OrderedDict()
        self._lock = asyncio.Lock()
        self._max_sessions = max_sessions

    async def load(self, session_id: str) -> SessionSnapshot | None:
        async with self._lock:
            snapshot = self._items.get(session_id)
            if snapshot is not None:
                # Move to end so it's treated as most-recently-used.
                self._items.move_to_end(session_id)
            return snapshot.clone() if snapshot is not None else None

    async def save(self, session_id: str, snapshot: SessionSnapshot) -> None:
        stored = snapshot.clone()
        stored.updated_at = datetime.now(UTC)
        async with self._lock:
            self._items[session_id] = stored
            self._items.move_to_end(session_id)
            while len(self._items) > self._max_sessions:
                self._items.popitem(last=False)

    async def delete(self, session_id: str) -> None:
        async with self._lock:
            self._items.pop(session_id, None)
