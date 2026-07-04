from __future__ import annotations

import asyncio
import json
import logging
from collections import Counter
from dataclasses import dataclass
from threading import Lock
from time import perf_counter
from typing import Any
from uuid import uuid4

from .models import Capability


@dataclass(frozen=True, slots=True)
class MetricKey:
    operation: str
    capability: str
    provider: str
    outcome: str


class RedisMetrics:
    """Redis-backed metrics store using INCR for cumulative counters.

    Writes are fire-and-forget (via ``asyncio.create_task``) to avoid
    blocking the request path on Redis latency.
    """

    def __init__(self, redis_client: Any, key_prefix: str = "ai_gateway") -> None:
        self._redis = redis_client
        self._prefix = key_prefix

    def record_request(
        self,
        *,
        operation: str,
        capability: str,
        provider: str,
        outcome: str,
        duration_ms: int,
    ) -> None:
        """Fire-and-forget increment of Redis counters."""
        req_key = f"{self._prefix}:requests_total:{operation}:{capability}:{provider}:{outcome}"
        dur_key = f"{self._prefix}:request_duration_ms_total:{operation}:{capability}:{provider}:{outcome}"
        asyncio.create_task(self._incr(req_key))
        asyncio.create_task(self._incrby(dur_key, duration_ms))

    async def _incr(self, key: str) -> None:
        try:
            await self._redis.incr(key)
        except Exception:
            logger = logging.getLogger(__name__)
            logger.warning("Redis metrics incr failed for key=%s", key, exc_info=True)

    async def _incrby(self, key: str, amount: int) -> None:
        try:
            await self._redis.incrby(key, amount)
        except Exception:
            logger = logging.getLogger(__name__)
            logger.warning("Redis metrics incrby failed for key=%s", key, exc_info=True)


class GatewayMetrics:
    def __init__(self, *, redis_metrics: RedisMetrics | None = None) -> None:
        self._lock = Lock()
        self._requests_total: Counter[MetricKey] = Counter()
        self._request_duration_ms_total: Counter[MetricKey] = Counter()
        self._redis = redis_metrics

    def record_request(
        self,
        *,
        operation: str,
        capability: Capability | str,
        provider: str | None,
        outcome: str,
        duration_ms: int,
    ) -> None:
        capability_str = capability.value if isinstance(capability, Capability) else capability
        provider_str = provider or "unknown"
        key = MetricKey(
            operation=operation,
            capability=capability_str,
            provider=provider_str,
            outcome=outcome,
        )
        with self._lock:
            self._requests_total[key] += 1
            self._request_duration_ms_total[key] += duration_ms
        if self._redis:
            self._redis.record_request(
                operation=operation,
                capability=capability_str,
                provider=provider_str,
                outcome=outcome,
                duration_ms=duration_ms,
            )

    def render_prometheus(self) -> str:
        lines = [
            "# HELP ai_gateway_requests_total Total gateway requests by operation.",
            "# TYPE ai_gateway_requests_total counter",
        ]
        sort_key = lambda item: (item.operation, item.capability, item.provider, item.outcome)
        for key in sorted(self._requests_total, key=sort_key):
            labels = (
                f'operation="{key.operation}",'
                f'capability="{key.capability}",'
                f'provider="{key.provider}",'
                f'outcome="{key.outcome}"'
            )
            lines.append(f"ai_gateway_requests_total{{{labels}}} {self._requests_total[key]}")
        lines.extend(
            [
                "# HELP ai_gateway_request_duration_ms_total Aggregate request duration in milliseconds.",
                "# TYPE ai_gateway_request_duration_ms_total counter",
            ]
        )
        for key in sorted(self._request_duration_ms_total, key=sort_key):
            labels = (
                f'operation="{key.operation}",'
                f'capability="{key.capability}",'
                f'provider="{key.provider}",'
                f'outcome="{key.outcome}"'
            )
            lines.append(
                "ai_gateway_request_duration_ms_total"
                f"{{{labels}}} {self._request_duration_ms_total[key]}"
            )
        return "\n".join(lines) + "\n"


class GatewayObservability:
    def __init__(
        self,
        *,
        logger: logging.Logger | None = None,
        metrics: GatewayMetrics | None = None,
    ) -> None:
        self.logger = logger or logging.getLogger("ai_gateway")
        self.metrics = metrics or GatewayMetrics()

    def new_trace_id(self) -> str:
        return uuid4().hex

    def ensure_trace_id(self, trace_id: str | None) -> str:
        return trace_id or self.new_trace_id()

    def log(self, level: int, event: str, **fields: object) -> None:
        payload = json.dumps(fields, ensure_ascii=False, sort_keys=True)
        self.logger.log(level, "%s %s", event, payload)

    def start_timer(self) -> float:
        return perf_counter()

    def finish_request(
        self,
        *,
        started_at: float,
        operation: str,
        capability: Capability | str,
        provider: str | None,
        outcome: str,
    ) -> int:
        duration_ms = int((perf_counter() - started_at) * 1000)
        self.metrics.record_request(
            operation=operation,
            capability=capability,
            provider=provider,
            outcome=outcome,
            duration_ms=duration_ms,
        )
        return duration_ms
