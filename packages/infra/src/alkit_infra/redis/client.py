from __future__ import annotations

from redis.asyncio import ConnectionPool, Redis

from loguru import logger

_pool: ConnectionPool | None = None
_client: Redis | None = None


def init_redis(
    url: str = "redis://localhost:6379/0",
    *,
    max_connections: int = 20,
    socket_timeout: float = 5.0,
    socket_connect_timeout: float = 3.0,
    retry_on_timeout: bool = True,
    decode_responses: bool = True,
    **extra_pool_kwargs: object,
) -> Redis:
    """Create the global connection pool and return an async Redis client.

    Safe to call multiple times — subsequent calls after the first are no-ops
    and return the existing client.
    """
    global _pool, _client

    if _client is not None:
        logger.debug("Redis client already initialized, reusing existing instance")
        return _client

    _pool = ConnectionPool.from_url(
        url,
        max_connections=max_connections,
        socket_timeout=socket_timeout,
        socket_connect_timeout=socket_connect_timeout,
        retry_on_timeout=retry_on_timeout,
        decode_responses=decode_responses,
        **extra_pool_kwargs,
    )
    _client = Redis(connection_pool=_pool)

    logger.info("Redis client initialized (url={})", url)
    return _client


def get_redis() -> Redis:
    """Return the initialised async Redis client.

    Raises :class:`RuntimeError` if :func:`init_redis` has not been called.
    """
    if _client is None:
        raise RuntimeError(
            "Redis client not initialized. Call init_redis() first."
        )
    return _client


async def close_redis() -> None:
    """Close the connection pool and reset global state."""
    global _pool, _client

    if _pool is not None:
        await _pool.aclose()
        logger.info("Redis connection pool closed")

    _pool = None
    _client = None
