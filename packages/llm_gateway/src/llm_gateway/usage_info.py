from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import UsageInfo


def normalize_usage(usage: UsageInfo | None) -> UsageInfo | None:
    if usage is None:
        return None
    total_tokens = usage.total_tokens
    if total_tokens is None and usage.input_tokens is not None and usage.output_tokens is not None:
        total_tokens = usage.input_tokens + usage.output_tokens
    return usage.model_copy(update={"total_tokens": total_tokens})


def accumulate_usage(total: UsageInfo | None, usage: UsageInfo | None) -> UsageInfo | None:
    normalized = normalize_usage(usage)
    if normalized is None:
        return total
    if total is None:
        return normalized
    return UsageInfo(
        input_tokens=_sum_optional_int(total.input_tokens, normalized.input_tokens),
        output_tokens=_sum_optional_int(total.output_tokens, normalized.output_tokens),
        total_tokens=_sum_optional_int(total.total_tokens, normalized.total_tokens),
        audio_duration_ms=_sum_optional_int(total.audio_duration_ms, normalized.audio_duration_ms),
        estimated_cost=_sum_optional_float(total.estimated_cost, normalized.estimated_cost),
        cache_write_tokens=_sum_optional_int(total.cache_write_tokens, normalized.cache_write_tokens),
        cache_read_tokens=_sum_optional_int(total.cache_read_tokens, normalized.cache_read_tokens),
    )


def usage_from_response_usage(usage: object | None) -> UsageInfo | None:
    if usage is None:
        return None
    input_tokens = getattr(usage, "input_tokens", None)
    prompt_tokens = getattr(usage, "prompt_tokens", None)
    output_tokens = getattr(usage, "output_tokens", None)
    completion_tokens = getattr(usage, "completion_tokens", None)
    estimated_cost = getattr(usage, "estimated_cost", None)
    if estimated_cost is None:
        estimated_cost = getattr(usage, "cost", None)
    return normalize_usage(
        UsageInfo(
            input_tokens=input_tokens if input_tokens is not None else prompt_tokens,
            output_tokens=output_tokens if output_tokens is not None else completion_tokens,
            total_tokens=getattr(usage, "total_tokens", None),
            estimated_cost=float(estimated_cost) if estimated_cost is not None else None,
            cache_write_tokens=getattr(usage, "cache_write_tokens", None),
            cache_read_tokens=getattr(usage, "cache_read_tokens", None),
        )
    )


def usage_from_openai_usage_payload(payload: Mapping[str, Any] | None) -> UsageInfo | None:
    if not isinstance(payload, Mapping):
        return None
    input_tokens = _read_usage_int(payload, "input_tokens")
    if input_tokens is None:
        input_tokens = _read_usage_int(payload, "prompt_tokens")
    output_tokens = _read_usage_int(payload, "output_tokens")
    if output_tokens is None:
        output_tokens = _read_usage_int(payload, "completion_tokens")
    total_tokens = _read_usage_int(payload, "total_tokens")
    if input_tokens is None and output_tokens is None and total_tokens is None:
        return None
    return normalize_usage(
        UsageInfo(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )
    )


def _sum_optional_int(left: int | None, right: int | None) -> int | None:
    if left is None:
        return right
    if right is None:
        return left
    return left + right


def _sum_optional_float(left: float | None, right: float | None) -> float | None:
    if left is None:
        return right
    if right is None:
        return left
    return left + right


def _read_usage_int(payload: Mapping[str, Any], key: str) -> int | None:
    value = payload.get(key)
    return value if isinstance(value, int) else None
