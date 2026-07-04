"""Retry policy for gateway dispatch with exponential backoff."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Controls retry behaviour when a provider call fails.

    Instances are created via :meth:`from_json` which merges caller-supplied
    overrides with sensible defaults.
    """

    max_attempts: int = 3
    retry_on_timeout: bool = True
    retry_on_rate_limit: bool = True
    retry_on_server_error: bool = True
    retry_on_auth_error: bool = False
    initial_backoff_ms: int = 500
    max_backoff_ms: int = 10_000
    backoff_multiplier: float = 2.0

    # ── Construction ────────────────────────────────────────────

    @classmethod
    def from_json(cls, data: Mapping[str, Any] | None) -> RetryPolicy:
        """Build a policy from a raw JSON mapping, ignoring unknown keys."""
        if not data:
            return cls()
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    # ── Runtime helpers ─────────────────────────────────────────

    def should_retry(self, error: Exception) -> bool:
        """Return *True* if *error* is retryable under this policy."""
        from ..errors import GatewayError, GatewayErrorCode

        if isinstance(error, GatewayError):
            if error.code == GatewayErrorCode.PROVIDER_TIMEOUT:
                return self.retry_on_timeout
            if error.code == GatewayErrorCode.PROVIDER_RATE_LIMITED:
                return self.retry_on_rate_limit
            if error.code == GatewayErrorCode.PROVIDER_AUTH_FAILED:
                return self.retry_on_auth_error
            if error.code == GatewayErrorCode.UPSTREAM_ERROR:
                return self.retry_on_server_error
        # Non-GatewayError exceptions (e.g. network errors) are retryable.
        return True

    def backoff_ms(self, attempt: int, *, retry_after_seconds: float | None = None) -> int:
        """Return the back-off delay in milliseconds for *attempt* (0-based).

        If the upstream provider returned a ``Retry-After`` header, its value
        (in seconds) is passed via *retry_after_seconds* and takes precedence
        over the computed exponential backoff.

        Jitter (uniform 50%-100% of computed delay) is applied to avoid
        thundering-herd effects when multiple callers retry simultaneously.
        """
        if retry_after_seconds is not None and retry_after_seconds > 0:
            base = retry_after_seconds * 1000
        else:
            base = min(
                self.initial_backoff_ms * (self.backoff_multiplier ** attempt),
                self.max_backoff_ms,
            )
        return int(base * random.uniform(0.5, 1.0))
