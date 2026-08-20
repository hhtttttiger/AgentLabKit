"""Tests for observability.span_processor — TraceBufferSpanProcessor."""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from observability.config import ObservabilitySettings
from observability.span_processor import (
    TraceBufferSpanProcessor,
    _deterministic_sample,
    _duration_ms,
    _sample_reason,
    _span_priority,
    _trace_status,
)


def _make_settings(**overrides) -> ObservabilitySettings:
    defaults = dict(
        enabled=True,
        max_spans_per_trace=100,
        max_attribute_bytes=4096,
        max_envelope_bytes=65536,
        publisher_queue_capacity=1000,
        slow_trace_threshold_ms=5000,
        normal_sample_rate=1.0,
    )
    defaults.update(overrides)
    return ObservabilitySettings(**defaults)


def _make_publisher() -> MagicMock:
    publisher = MagicMock()
    publisher.submit_nowait = MagicMock()
    return publisher


# ── Helper functions ───────────────────────────────────────────────────


class TestHelperFunctions:
    def test_duration_ms_basic(self) -> None:
        start = 1_000_000_000  # 1s in ns
        end = 1_500_000_000    # 1.5s in ns
        assert _duration_ms(start, end) == 500

    def test_duration_ms_none_inputs(self) -> None:
        assert _duration_ms(None, 100) == 0
        assert _duration_ms(100, None) == 0
        assert _duration_ms(None, None) == 0

    def test_duration_ms_negative_clamped(self) -> None:
        assert _duration_ms(200, 100) == 0

    def test_sample_reason_error_status(self) -> None:
        assert _sample_reason("error", 100, 5000) == "error"

    def test_sample_reason_timeout_status(self) -> None:
        assert _sample_reason("timeout", 100, 5000) == "timeout"

    def test_sample_reason_slow(self) -> None:
        assert _sample_reason("ok", 6000, 5000) == "slow"

    def test_sample_reason_normal(self) -> None:
        assert _sample_reason("ok", 100, 5000) == "normal"

    def test_deterministic_sample_rate_1(self) -> None:
        assert _deterministic_sample("abc", 1.0) is True

    def test_deterministic_sample_rate_0(self) -> None:
        assert _deterministic_sample("abc", 0.0) is False

    def test_deterministic_sample_is_stable(self) -> None:
        result1 = _deterministic_sample("a" * 32, 0.5)
        result2 = _deterministic_sample("a" * 32, 0.5)
        assert result1 == result2


class TestSpanPriority:
    def test_agent_run_highest(self) -> None:
        span = MagicMock()
        span.name = "agent.run"
        span.status = "ok"
        assert _span_priority(span) == 100

    def test_error_span_high(self) -> None:
        span = MagicMock()
        span.name = "other"
        span.status = "error"
        assert _span_priority(span) == 90

    def test_llm_generate_medium(self) -> None:
        span = MagicMock()
        span.name = "llm.generate"
        span.status = "ok"
        assert _span_priority(span) == 70

    def test_tool_execute_medium(self) -> None:
        span = MagicMock()
        span.name = "tool.execute"
        span.status = "ok"
        assert _span_priority(span) == 70

    def test_other_low(self) -> None:
        span = MagicMock()
        span.name = "custom.span"
        span.status = "ok"
        assert _span_priority(span) == 10


# ── TraceBufferSpanProcessor ───────────────────────────────────────────


class TestTraceBufferSpanProcessor:
    def test_snapshot_empty(self) -> None:
        settings = _make_settings()
        publisher = _make_publisher()
        processor = TraceBufferSpanProcessor(publisher, settings)
        snap = processor.snapshot()
        assert snap["active_traces"] == 0
        assert snap["buffered_spans"] == 0
        assert snap["buffer_overflow_dropped"] == 0

    def test_shutdown_clears_state(self) -> None:
        settings = _make_settings()
        publisher = _make_publisher()
        processor = TraceBufferSpanProcessor(publisher, settings)
        processor.shutdown()
        snap = processor.snapshot()
        assert snap["active_traces"] == 0

    def test_force_flush_returns_true(self) -> None:
        settings = _make_settings()
        publisher = _make_publisher()
        processor = TraceBufferSpanProcessor(publisher, settings)
        assert processor.force_flush() is True

    def test_on_end_disabled_settings(self) -> None:
        settings = _make_settings(enabled=False)
        publisher = _make_publisher()
        processor = TraceBufferSpanProcessor(publisher, settings)
        # Should not raise even with None span
        processor.on_end(None)
        publisher.submit_nowait.assert_not_called()

    def test_on_end_no_context_ignored(self) -> None:
        settings = _make_settings()
        publisher = _make_publisher()
        processor = TraceBufferSpanProcessor(publisher, settings)
        span = MagicMock()
        span.context = None
        processor.on_end(span)
        publisher.submit_nowait.assert_not_called()
