"""Tests for observability.contracts — Pydantic model validation."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from observability.contracts import (
    SpanEnvelope,
    TraceEnvelope,
    TraceRecord,
    TraceStats,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _make_span(**overrides) -> SpanEnvelope:
    defaults = dict(
        span_id="a" * 16,
        trace_id="b" * 32,
        name="test.span",
        kind="internal",
        status="ok",
        started_at_utc=_utcnow(),
        completed_at_utc=_utcnow(),
        duration_ms=100,
    )
    defaults.update(overrides)
    return SpanEnvelope(**defaults)


def _make_trace(**overrides) -> TraceEnvelope:
    now = _utcnow()
    root = _make_span(span_id="c" * 16, trace_id="d" * 32)
    defaults = dict(
        trace_id="d" * 32,
        root_span_id="c" * 16,
        run_id=str(uuid4()),
        started_at_utc=now,
        completed_at_utc=now,
        total_duration_ms=100,
        span_count=1,
        spans=[root],
    )
    defaults.update(overrides)
    return TraceEnvelope(**defaults)


# ── SpanEnvelope ───────────────────────────────────────────────────────


class TestSpanEnvelope:
    def test_valid_span(self) -> None:
        span = _make_span()
        assert span.span_id == "a" * 16
        assert span.status == "ok"

    def test_invalid_span_id_pattern(self) -> None:
        with pytest.raises(Exception):
            _make_span(span_id="invalid")

    def test_invalid_trace_id_pattern(self) -> None:
        with pytest.raises(Exception):
            _make_span(trace_id="short")

    def test_negative_duration_rejected(self) -> None:
        with pytest.raises(Exception):
            _make_span(duration_ms=-1)

    def test_parent_span_id_optional(self) -> None:
        span = _make_span(parent_span_id=None)
        assert span.parent_span_id is None

    def test_parent_span_id_valid(self) -> None:
        span = _make_span(parent_span_id="e" * 16)
        assert span.parent_span_id == "e" * 16


# ── TraceEnvelope ──────────────────────────────────────────────────────


class TestTraceEnvelope:
    def test_valid_trace(self) -> None:
        trace = _make_trace()
        assert trace.schema_version == 1
        assert trace.span_count == 1
        assert len(trace.spans) == 1

    def test_span_count_mismatch_rejected(self) -> None:
        root = _make_span(span_id="c" * 16, trace_id="d" * 32)
        with pytest.raises(Exception, match="span_count"):
            _make_trace(span_count=2, spans=[root])

    def test_root_span_not_in_spans_rejected(self) -> None:
        other = _make_span(span_id="f" * 16, trace_id="d" * 32)
        with pytest.raises(Exception, match="root_span_id"):
            _make_trace(root_span_id="c" * 16, spans=[other])

    def test_span_trace_id_mismatch_rejected(self) -> None:
        wrong_trace = _make_span(span_id="c" * 16, trace_id="e" * 32)
        with pytest.raises(Exception, match="trace_id"):
            _make_trace(trace_id="d" * 32, spans=[wrong_trace])

    def test_invalid_run_id_rejected(self) -> None:
        with pytest.raises(Exception):
            _make_trace(run_id="not-a-uuid")

    def test_cost_defaults_to_zero(self) -> None:
        trace = _make_trace()
        assert trace.total_estimated_cost == Decimal("0")

    def test_tokens_default_to_zero(self) -> None:
        trace = _make_trace()
        assert trace.total_input_tokens == 0
        assert trace.total_output_tokens == 0
        assert trace.cache_write_tokens == 0
        assert trace.cache_read_tokens == 0


# ── TraceRecord ────────────────────────────────────────────────────────


class TestTraceRecord:
    def test_from_attributes(self) -> None:
        """TraceRecord should support from_attributes for ORM mapping."""

        class FakeOrm:
            trace_id = "a" * 32
            root_span_id = "b" * 16
            run_id = str(uuid4())
            status = "ok"
            started_at_utc = _utcnow()
            completed_at_utc = _utcnow()
            total_duration_ms = 100
            span_count = 1

        record = TraceRecord.model_validate(FakeOrm(), from_attributes=True)
        assert record.trace_id == "a" * 32
        assert record.status == "ok"


# ── TraceStats ─────────────────────────────────────────────────────────


class TestTraceStats:
    def test_defaults(self) -> None:
        stats = TraceStats()
        assert stats.total_traces == 0
        assert stats.error_count == 0
        assert stats.p95_duration_ms == 0
