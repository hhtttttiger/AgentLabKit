from __future__ import annotations

import logging
import time
from typing import Protocol

from .domain import ModelCatalogSnapshot

logger = logging.getLogger(__name__)


class CatalogCache(Protocol):
    async def get(self) -> ModelCatalogSnapshot | None: ...

    async def set(self, snapshot: ModelCatalogSnapshot) -> None: ...

    async def invalidate(self) -> None: ...


class NoOpCatalogCache:
    async def get(self) -> ModelCatalogSnapshot | None:
        return None

    async def set(self, snapshot: ModelCatalogSnapshot) -> None:
        del snapshot

    async def invalidate(self) -> None:
        return None


class InMemoryCatalogCache:
    """In-memory catalog snapshot cache with TTL-based expiry.

    Stores a single ``ModelCatalogSnapshot`` in-process.  The cached value
    is considered valid for *ttl_seconds* after it was last set.  Callers
    (``ModelCatalogService``) can force a bypass via *force_refresh=True*
    or proactively clear the cache via :meth:`invalidate`.
    """

    def __init__(self, ttl_seconds: float = 30.0) -> None:
        self._ttl = ttl_seconds
        self._snapshot: ModelCatalogSnapshot | None = None
        self._cached_at: float = 0.0

    async def get(self) -> ModelCatalogSnapshot | None:
        if self._snapshot is None:
            return None
        if time.monotonic() - self._cached_at > self._ttl:
            logger.debug("Catalog cache expired (ttl=%.1fs)", self._ttl)
            return None
        return self._snapshot

    async def set(self, snapshot: ModelCatalogSnapshot) -> None:
        self._snapshot = snapshot
        self._cached_at = time.monotonic()
        logger.debug(
            "Catalog cache refreshed (revision=%d)",
            snapshot.revision,
        )

    async def invalidate(self) -> None:
        self._snapshot = None
        logger.debug("Catalog cache invalidated")
