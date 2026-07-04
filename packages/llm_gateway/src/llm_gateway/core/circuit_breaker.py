"""Per-instance circuit breaker (closed → open → half-open → closed)."""

from __future__ import annotations

import asyncio
import time
from enum import Enum


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Stateful circuit breaker for a single upstream provider instance.

    Parameters
    ----------
    failure_threshold:
        Consecutive failures before the circuit opens.
    recovery_timeout:
        Seconds to wait in OPEN before moving to HALF_OPEN for a probe.
    half_open_max_calls:
        Number of successful probes needed to close the circuit again.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_max_calls = half_open_max_calls
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._half_open_in_flight = 0
        self._lock = asyncio.Lock()

    # -- state inspection ----------------------------------------------------

    @property
    def state(self) -> CircuitState:
        """Return the *effective* state, auto-transitioning OPEN → HALF_OPEN."""
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self._recovery_timeout:
                return CircuitState.HALF_OPEN
        return self._state

    # -- request gating ------------------------------------------------------

    async def allow_request(self) -> bool:
        """Return ``True`` if a request may proceed under the current state."""
        async with self._lock:
            s = self.state
            if s == CircuitState.CLOSED:
                return True
            if s == CircuitState.OPEN:
                return False
            # HALF_OPEN: allow a limited number of probe requests.
            if self._half_open_in_flight < self._half_open_max_calls:
                self._half_open_in_flight += 1
                return True
            return False

    # -- outcome recording ---------------------------------------------------

    async def record_success(self) -> None:
        """Record a successful response."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self._half_open_max_calls:
                    self._reset()
            else:
                # In CLOSED state, successes reset the failure counter.
                self._failure_count = 0

    async def record_failure(self) -> None:
        """Record a failed response."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._state == CircuitState.HALF_OPEN:
                # A failure during half-open trips the breaker again.
                self._trip()
            elif self._failure_count >= self._failure_threshold:
                self._trip()

    # -- internal state transitions ------------------------------------------

    def _trip(self) -> None:
        self._state = CircuitState.OPEN
        self._success_count = 0
        self._half_open_in_flight = 0

    def _reset(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_in_flight = 0
