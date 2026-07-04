"""Simple token-bucket rate limiter for upstream provider instances."""

from __future__ import annotations

import asyncio
import time


class TokenBucketRateLimiter:
    """Async token-bucket rate limiter.

    Parameters
    ----------
    rate:
        Tokens added per second (i.e. sustained request rate).
    capacity:
        Maximum burst size — how many requests can be dispatched
        instantaneously before the limiter starts throttling.
    """

    def __init__(self, rate: float, capacity: float) -> None:
        self._rate = rate
        self._capacity = capacity
        self._tokens = capacity
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Block until a token is available."""
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self._last_refill
                self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
                self._last_refill = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
            # Busy-wait in short intervals so we don't overshoot.
            await asyncio.sleep(0.05)
