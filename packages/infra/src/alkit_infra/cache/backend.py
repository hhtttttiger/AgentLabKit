from __future__ import annotations

import asyncio
import time
from typing import Any, Protocol, runtime_checkable

from loguru import logger


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class CacheBackend(Protocol):
    """Minimal async cache contract.

    Implementations must support string keys and string values.  Callers
    that need structured data should serialise / deserialise externally
    (e.g. via ``json.dumps`` / ``json.loads``).
    """

    async def get(self, key: str) -> str | None:
        """Return the value for *key*, or ``None`` if missing / expired."""
        ...

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """Store *value* under *key* with an optional TTL in seconds."""
        ...

    async def delete(self, key: str) -> None:
        """Remove *key* from the cache.  No-op if the key does not exist."""
        ...

    async def exists(self, key: str) -> bool:
        """Return ``True`` if *key* exists and has not expired."""
        ...

    async def get_many(self, keys: list[str]) -> list[str | None]:
        """Bulk get — returns values in the same order as *keys*."""
        ...

    async def set_many(self, mapping: dict[str, str], ttl: int | None = None) -> None:
        """Bulk set — store every key/value pair in *mapping*."""
        ...

    async def delete_many(self, keys: list[str]) -> None:
        """Bulk delete.  No-op for keys that do not exist."""
        ...

    async def acquire_lock(
        self,
        name: str,
        ttl: int,
        *,
        blocking_timeout: float = 0,
    ) -> bool:
        """Try to acquire a distributed lock.

        Returns ``True`` if the lock was acquired, ``False`` otherwise.
        *blocking_timeout* seconds to wait (0 = non-blocking).
        """
        ...

    async def release_lock(self, name: str) -> None:
        """Release a previously acquired lock."""
        ...


# ---------------------------------------------------------------------------
# Redis implementation
# ---------------------------------------------------------------------------

class RedisCache:
    """ :class:`CacheBackend` backed by an async Redis connection.

    If no *redis* client is provided, the global client from
    :func:`alkit_infra.redis.client.get_redis` is used.
    """

    def __init__(self, redis: Any | None = None) -> None:
        # Import lazily to keep the module importable without Redis at type-check time.
        if redis is not None:
            self._redis = redis
        else:
            from alkit_infra.redis.client import get_redis

            self._redis = get_redis()

    # -- single key ----------------------------------------------------------

    async def get(self, key: str) -> str | None:
        return await self._redis.get(key)

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        if ttl is not None:
            await self._redis.set(key, value, ex=ttl)
        else:
            await self._redis.set(key, value)

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self._redis.exists(key))

    # -- bulk ----------------------------------------------------------------

    async def get_many(self, keys: list[str]) -> list[str | None]:
        if not keys:
            return []
        result: list[str | None] = await self._redis.mget(keys)
        return result

    async def set_many(self, mapping: dict[str, str], ttl: int | None = None) -> None:
        if not mapping:
            return
        await self._redis.mset(mapping)
        if ttl is not None:
            # mset doesn't support per-key TTL; set expiry individually.
            for key in mapping:
                await self._redis.expire(key, ttl)

    async def delete_many(self, keys: list[str]) -> None:
        if not keys:
            return
        await self._redis.delete(*keys)

    # -- locking -------------------------------------------------------------

    async def acquire_lock(
        self,
        name: str,
        ttl: int,
        *,
        blocking_timeout: float = 0,
    ) -> bool:
        lock = self._redis.lock(name, timeout=ttl)
        return await lock.acquire(blocking_timeout=blocking_timeout)

    async def release_lock(self, name: str) -> None:
        lock = self._redis.lock(name)
        try:
            await lock.release()
        except Exception:
            logger.opt(exception=True).debug("Failed to release lock {}", name)


# ---------------------------------------------------------------------------
# In-memory implementation (dev / testing)
# ---------------------------------------------------------------------------

class InMemoryCache:
    """Thread-safe, dict-backed :class:`CacheBackend` for local development.

    TTL is tracked via ``time.monotonic()`` and lazily evicted on access.
    Locking is implemented with :class:`asyncio.Lock` — only works within a
    single process.
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float | None]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    # -- internal helpers ----------------------------------------------------

    def _is_expired(self, expires_at: float | None) -> bool:
        if expires_at is None:
            return False
        return time.monotonic() >= expires_at

    def _evict(self, key: str) -> None:
        if key in self._store and self._is_expired(self._store[key][1]):
            del self._store[key]

    # -- single key ----------------------------------------------------------

    async def get(self, key: str) -> str | None:
        self._evict(key)
        entry = self._store.get(key)
        if entry is None:
            return None
        return entry[0]

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        expires_at = time.monotonic() + ttl if ttl is not None else None
        self._store[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def exists(self, key: str) -> bool:
        self._evict(key)
        return key in self._store

    # -- bulk ----------------------------------------------------------------

    async def get_many(self, keys: list[str]) -> list[str | None]:
        return [await self.get(k) for k in keys]

    async def set_many(self, mapping: dict[str, str], ttl: int | None = None) -> None:
        for k, v in mapping.items():
            await self.set(k, v, ttl=ttl)

    async def delete_many(self, keys: list[str]) -> None:
        for k in keys:
            self._store.pop(k, None)

    # -- locking -------------------------------------------------------------

    async def acquire_lock(
        self,
        name: str,
        ttl: int,
        *,
        blocking_timeout: float = 0,
    ) -> bool:
        lock = self._locks.get(name)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[name] = lock

        try:
            acquired = await asyncio.wait_for(
                lock.acquire(),
                timeout=blocking_timeout if blocking_timeout > 0 else 0.001,
            )
            return acquired
        except asyncio.TimeoutError:
            return False

    async def release_lock(self, name: str) -> None:
        lock = self._locks.get(name)
        if lock is not None and lock.locked():
            lock.release()
