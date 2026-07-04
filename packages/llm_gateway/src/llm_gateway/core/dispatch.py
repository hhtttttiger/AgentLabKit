"""Dispatch session helper — shared fault-tolerance boilerplate for gateway dispatch.

The :class:`_DispatchSession` class encapsulates breaker checking, rate
limiting, error handling, retry logic, and observability recording that is
common to both unary and streaming dispatch paths.  The two dispatch methods
in :class:`GatewayService` delegate to it, shrinking from ~120 lines each
to ~30 lines of orchestration.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any, Callable, Awaitable, TypeVar

from ..errors import GatewayError, GatewayErrorCode
from ..model_catalog.retry_policy import RetryPolicy
from ..models import Capability, UsageInfo
from ..provider_runtime import RuntimeProviderConfig
from ..usage_info import accumulate_usage
from .circuit_breaker import CircuitBreaker
from .rate_limiter import TokenBucketRateLimiter

logger = logging.getLogger(__name__)

T_Request = TypeVar("T_Request")
T_Response = TypeVar("T_Response")
T_Event = TypeVar("T_Event")

# ── Strategy types ────────────────────────────────────────────────────────────

UnaryInvoker = Callable[[Any, T_Request, RuntimeProviderConfig], Awaitable[T_Response]]
StreamInvoker = Callable[[Any, T_Request, RuntimeProviderConfig], AsyncIterator[T_Event]]


def _pricing_from_route(route: Any) -> dict[str, Any]:
    """Extract pricing kwargs from a route for ``_record_usage``."""
    return {
        "input_price_per_mtok": getattr(route, "input_price_per_mtok", None),
        "output_price_per_mtok": getattr(route, "output_price_per_mtok", None),
        "cache_write_price_per_mtok": getattr(route, "cache_write_price_per_mtok", None),
        "cache_read_price_per_mtok": getattr(route, "cache_read_price_per_mtok", None),
    }


class _DispatchSession:
    """Encapsulates mutable state and shared logic for a dispatch operation.

    Both ``_dispatch_unary`` and ``_dispatch_stream`` create one session per
    request and delegate fault-tolerance boilerplate to it.
    """

    def __init__(
        self,
        gateway: Any,  # GatewayService (avoid circular import)
        capability: Capability,
        candidates: list[Any],
        retry_policy: RetryPolicy,
        trace_id: str,
        request: Any,
    ) -> None:
        self._gw = gateway
        self.capability = capability
        self.candidates = candidates
        self.retry_policy = retry_policy
        self.trace_id = trace_id
        self.request = request
        self.started_at = self._gw.observability.start_timer()
        self.last_error: Exception | None = None

    # ── Candidate iteration helpers ───────────────────────────────────────────

    def _is_final_attempt(self, attempt_no: int) -> bool:
        return attempt_no >= self.retry_policy.max_attempts or attempt_no >= len(self.candidates)

    # ── Fault-tolerance gate (breaker + limiter) ─────────────────────────────

    async def enter_route(self, route: Any) -> tuple[CircuitBreaker | None, TokenBucketRateLimiter | None]:
        """Check circuit breaker and acquire rate limiter for *route*.

        Returns both so the caller can record success/failure later.
        """
        breaker = self._gw._get_circuit_breaker(route)
        if breaker and not await breaker.allow_request():
            raise GatewayError(
                GatewayErrorCode.UPSTREAM_ERROR,
                f"Circuit breaker open for instance {route.instance_key}",
                provider=route.provider,
                model=route.model_key,
            )
        limiter = self._gw._get_rate_limiter(route)
        if limiter:
            await limiter.acquire()
        return breaker, limiter

    # ── Error handling ────────────────────────────────────────────────────────

    async def handle_failure(
        self,
        route: Any,
        error: Exception,
        attempt_no: int,
        *,
        usage: UsageInfo | None = None,
        breaker: CircuitBreaker | None = None,
    ) -> bool:
        """Record the failure and decide whether to retry.

        Returns ``True`` if the caller should retry (after an appropriate
        backoff sleep), ``False`` if the error should be re-raised.
        """
        self.last_error = error
        if breaker:
            await breaker.record_failure()
        self._gw._record_failure(
            started_at=self.started_at,
            capability=self.capability,
            provider=route.provider,
            model=route.model_key,
            trace_id=self.trace_id,
            operation=self.capability.value,
            error=error,
        )
        is_final = self._is_final_attempt(attempt_no)
        await self._gw._record_usage(
            request_id=self.trace_id or "unknown",
            model_key=route.model_key,
            instance_key=route.instance_key,
            capability=self.capability,
            success=False,
            response=None,
            started_at=self.started_at,
            error=error,
            usage=usage,
            attempt_no=attempt_no,
            is_final=is_final and not self.retry_policy.should_retry(error),
            total_attempts=attempt_no,
            **_pricing_from_route(route),
        )
        if is_final or not self.retry_policy.should_retry(error):
            return False  # do not retry
        retry_after = getattr(error, "retry_after", None)
        backoff = self.retry_policy.backoff_ms(attempt_no - 1, retry_after_seconds=retry_after)
        logger.info(
            "Retrying %s on instance %s (attempt %d/%d, backoff %dms)",
            self.capability.value, route.instance_key, attempt_no, self.retry_policy.max_attempts, backoff,
        )
        await asyncio.sleep(backoff / 1000)
        return True  # caller should retry

    # ── Success recording ─────────────────────────────────────────────────────

    async def handle_success(
        self,
        route: Any,
        *,
        usage: UsageInfo | None = None,
        event_count: int | None = None,
        breaker: CircuitBreaker | None = None,
    ) -> None:
        """Record a successful response."""
        if breaker:
            await breaker.record_success()
        self._gw._record_success(
            started_at=self.started_at,
            capability=self.capability,
            provider=route.provider,
            model=route.model_key,
            trace_id=self.trace_id,
            operation=self.capability.value,
            event_count=event_count,
        )
        await self._gw._record_usage(
            request_id=self.trace_id or "unknown",
            model_key=route.model_key,
            instance_key=route.instance_key,
            capability=self.capability,
            success=True,
            response=None,
            started_at=self.started_at,
            error=None,
            usage=usage,
            attempt_no=1,
            is_final=True,
            total_attempts=1,
            **_pricing_from_route(route),
        )

    # ── Route preparation ─────────────────────────────────────────────────────

    def prepare_route(self, route: Any) -> tuple[Any, Any]:
        """Resolve adapter and rewrite request for a route.

        Returns ``(adapter, upstream_request)``.
        """
        adapter = self._gw.registry.resolve_adapter(self.capability, provider=route.provider)
        upstream_request = self._gw._rewrite_request_model(self.request, route)
        return adapter, upstream_request
