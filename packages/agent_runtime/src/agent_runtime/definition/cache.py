"""In-memory cache for agent definition snapshots with revision-based invalidation."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Protocol

from .models import AgentDefinitionSnapshot

logger = logging.getLogger(__name__)


class AgentDefinitionCache(Protocol):
    """Protocol for agent definition caching."""

    async def get(self, agent_key: str, version: int | None = None) -> AgentDefinitionSnapshot | None:
        """Get cached definition. version=None means current published."""
        ...

    async def put(self, snapshot: AgentDefinitionSnapshot) -> None:
        """Cache a definition snapshot."""
        ...

    async def invalidate(self, agent_key: str | None = None) -> None:
        """Invalidate cache. agent_key=None invalidates all."""
        ...

    async def get_revision(self) -> int:
        """Get the last-known catalog revision number."""
        ...

    async def set_revision(self, revision: int) -> None:
        """Update the last-known catalog revision number."""
        ...


class InMemoryAgentDefinitionCache:
    """Simple in-memory cache with TTL and revision tracking.

    Uses agent_key as primary key. For version-specific lookups,
    uses (agent_key, version_number) as composite key.
    """

    def __init__(self, ttl_seconds: float = 60.0) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[AgentDefinitionSnapshot, float]] = {}
        self._revision: int = 0
        self._lock = asyncio.Lock()

    async def get(self, agent_key: str, version: int | None = None) -> AgentDefinitionSnapshot | None:
        key = self._cache_key(agent_key, version)
        entry = self._store.get(key)
        if entry is None:
            return None
        snapshot, ts = entry
        if time.monotonic() - ts > self._ttl:
            del self._store[key]
            return None
        return snapshot

    async def put(self, snapshot: AgentDefinitionSnapshot) -> None:
        now = time.monotonic()
        # Cache under both the versioned key and the "current published" key
        self._store[self._cache_key(snapshot.agent_key, snapshot.version_number)] = (snapshot, now)
        self._store[self._cache_key(snapshot.agent_key, None)] = (snapshot, now)

    async def invalidate(self, agent_key: str | None = None) -> None:
        if agent_key is None:
            self._store.clear()
            logger.debug("Agent definition cache fully invalidated")
        else:
            keys_to_remove = [k for k in self._store if k.startswith(f"{agent_key}:")]
            for k in keys_to_remove:
                del self._store[k]
            logger.debug("Agent definition cache invalidated for %s", agent_key)

    async def get_revision(self) -> int:
        return self._revision

    async def set_revision(self, revision: int) -> None:
        self._revision = revision

    @staticmethod
    def _cache_key(agent_key: str, version: int | None) -> str:
        return f"{agent_key}:{version or 'published'}"
