"""Tests for CostProjector — RuntimeEvent v2 → CostRecord.

Phase 5: tests use real RuntimeEvent dataclasses where possible.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from cost_analysis.contracts import CostRecord
from cost_analysis.projector import CostProjector

# Import real v2 event classes (5.4)
from agent_runtime.events_v2 import LLMCallCompleted, LLMCallFailed


class FakePublisher:
    """收集 submit_nowait 调用的 fake publisher。"""

    def __init__(self) -> None:
        self.submitted: list[CostRecord] = []

    def submit_nowait(self, record: CostRecord) -> None:
        self.submitted.append(record)


def _ts(minutes: int = 0) -> datetime:
    return datetime(2026, 8, 28, 12, minutes, 0, tzinfo=timezone.utc)


def _make_event(event_type: str, run_id: str = "", **kwargs):
    ts = kwargs.pop("timestamp", _ts(1))
    started_at = kwargs.pop("started_at", _ts(0))
    return SimpleNamespace(
        event_type=event_type,
        event_id=uuid4().hex,
        run_id=run_id or uuid4().hex,
        trace_id=uuid4().hex,
        span_id=uuid4().hex[:16],
        timestamp=ts,
        started_at=started_at,
        attributes={},
        **kwargs,
    )


@pytest.fixture()
def projector():
    return CostProjector(FakePublisher())


# ── LLM Call Completed ─────────────────────────────────────────────


class TestLLMCallCompleted:
    def test_basic_cost_record(self, projector: CostProjector):
        run_id = uuid4().hex
        event = _make_event(
            "llm.call_completed",
            run_id=run_id,
            model="gpt-4o",
            provider="openai",
            input_tokens=100,
            output_tokens=50,
            estimated_cost=Decimal("0.003"),
        )
        import asyncio
        asyncio.run(projector.handle(event))
        assert len(projector._publisher.submitted) == 1
        record = projector._publisher.submitted[0]
        assert record.run_id == run_id
        assert record.model == "gpt-4o"
        assert record.provider == "openai"
        assert record.input_tokens == 100
        assert record.output_tokens == 50
        assert record.estimated_cost == 0.003

    def test_cache_tokens_recorded(self, projector: CostProjector):
        run_id = uuid4().hex
        event = _make_event(
            "llm.call_completed",
            run_id=run_id,
            model="gpt-4o",
            provider="openai",
            input_tokens=100,
            output_tokens=50,
            cache_write_tokens=20,
            cache_read_tokens=10,
            estimated_cost=Decimal("0.002"),
        )
        import asyncio
        asyncio.run(projector.handle(event))
        record = projector._publisher.submitted[0]
        assert record.cache_write_tokens == 20
        assert record.cache_read_tokens == 10

    def test_agent_key_captured(self, projector: CostProjector):
        run_id = uuid4().hex
        event = _make_event(
            "llm.call_completed",
            run_id=run_id,
            agent_key="chat",
            model="gpt-4o",
            provider="openai",
            input_tokens=100,
            output_tokens=50,
            estimated_cost=Decimal("0.003"),
        )
        import asyncio
        asyncio.run(projector.handle(event))
        record = projector._publisher.submitted[0]
        assert record.agent_key == "chat"

    def test_none_tokens_default_to_zero(self, projector: CostProjector):
        run_id = uuid4().hex
        event = _make_event(
            "llm.call_completed",
            run_id=run_id,
            model="gpt-4o",
            provider="openai",
            input_tokens=None,
            output_tokens=None,
            estimated_cost=None,
        )
        import asyncio
        asyncio.run(projector.handle(event))
        record = projector._publisher.submitted[0]
        assert record.input_tokens == 0
        assert record.output_tokens == 0
        assert record.estimated_cost == 0.0

    def test_duration_calculated(self, projector: CostProjector):
        run_id = uuid4().hex
        event = _make_event(
            "llm.call_completed",
            run_id=run_id,
            model="gpt-4o",
            provider="openai",
            input_tokens=100,
            output_tokens=50,
            estimated_cost=Decimal("0.003"),
            started_at=_ts(0),
            timestamp=_ts(1),
        )
        import asyncio
        asyncio.run(projector.handle(event))
        record = projector._publisher.submitted[0]
        assert record.started_at_utc == _ts(0)
        assert record.completed_at_utc == _ts(1)


# ── LLM Call Failed ────────────────────────────────────────────────


class TestLLMCallFailed:
    def test_failed_cost_record_zero_cost(self, projector: CostProjector):
        run_id = uuid4().hex
        event = _make_event(
            "llm.call_failed",
            run_id=run_id,
            model="gpt-4o",
            provider="openai",
            error_code="TIMEOUT",
            error_message="request timeout",
        )
        import asyncio
        asyncio.run(projector.handle(event))
        assert len(projector._publisher.submitted) == 1
        record = projector._publisher.submitted[0]
        assert record.run_id == run_id
        assert record.input_tokens == 0
        assert record.output_tokens == 0
        assert record.estimated_cost == 0.0
        assert record.error_code == "TIMEOUT"
        assert record.error_message == "request timeout"


# ── Edge Cases ─────────────────────────────────────────────────────


class TestEdgeCases:
    def test_non_v2_event_ignored(self, projector: CostProjector):
        """旧事件（无 event_type 属性）应被忽略。"""
        old_event = SimpleNamespace(name="llm_call_completed", trace_id="t1")
        import asyncio
        asyncio.run(projector.handle(old_event))
        assert len(projector._publisher.submitted) == 0

    def test_empty_run_id_ignored(self, projector: CostProjector):
        event = SimpleNamespace(
            event_type="llm.call_completed",
            event_id=uuid4().hex,
            run_id="",
            trace_id=uuid4().hex,
            span_id=uuid4().hex[:16],
            timestamp=_ts(1),
            started_at=_ts(0),
            attributes={},
            model="gpt-4o",
            provider="openai",
            input_tokens=100,
            output_tokens=50,
            estimated_cost=Decimal("0.003"),
        )
        import asyncio
        asyncio.run(projector.handle(event))
        assert len(projector._publisher.submitted) == 0

    def test_other_event_types_ignored(self, projector: CostProjector):
        """非 LLM 事件应被忽略。"""
        event = _make_event("run.started", run_id=uuid4().hex)
        import asyncio
        asyncio.run(projector.handle(event))
        assert len(projector._publisher.submitted) == 0

    def test_publisher_error_does_not_raise(self, projector: CostProjector):
        class BrokenPublisher:
            def submit_nowait(self, record):
                raise RuntimeError("queue full")

        projector._publisher = BrokenPublisher()
        event = _make_event(
            "llm.call_completed",
            run_id=uuid4().hex,
            model="gpt-4o",
            provider="openai",
            input_tokens=100,
            output_tokens=50,
            estimated_cost=Decimal("0.003"),
        )
        import asyncio
        asyncio.run(projector.handle(event))  # should not raise

    def test_multiple_records_independent(self, projector: CostProjector):
        r1 = uuid4().hex
        r2 = uuid4().hex
        import asyncio
        asyncio.run(projector.handle(_make_event(
            "llm.call_completed", run_id=r1,
            model="gpt-4o", provider="openai",
            input_tokens=100, output_tokens=50,
            estimated_cost=Decimal("0.003"),
        )))
        asyncio.run(projector.handle(_make_event(
            "llm.call_completed", run_id=r2,
            model="claude-sonnet-5", provider="anthropic",
            input_tokens=200, output_tokens=100,
            estimated_cost=Decimal("0.006"),
        )))
        assert len(projector._publisher.submitted) == 2
        assert projector._publisher.submitted[0].run_id == r1
        assert projector._publisher.submitted[1].run_id == r2


# ── Real RuntimeEvent tests (5.4) ─────────────────────────────────


class TestRealEventContract:
    """Tests using real RuntimeEvent dataclasses to prevent contract drift."""

    def test_real_llm_completed_event(self, projector: CostProjector):
        """CostProjector must work with real LLMCallCompleted (5.4)."""
        run_id = uuid4().hex
        trace_id = uuid4().hex
        span_id = uuid4().hex[:16]
        event = LLMCallCompleted(
            run_id=run_id,
            trace_id=trace_id,
            span_id=span_id,
            model="gpt-4o",
            provider="openai",
            input_tokens=150,
            output_tokens=80,
            cache_write_tokens=10,
            cache_read_tokens=5,
            estimated_cost=0.003,
            latency_ms=1200,
            finish_reason="stop",
            agent_key="chat",
            started_at=_ts(0),
            completed_at=_ts(1),
        )
        import asyncio
        asyncio.run(projector.handle(event))
        record = projector._publisher.submitted[0]
        # Identity comes from event (5.2)
        assert record.run_id == run_id
        assert record.trace_id == trace_id
        assert record.span_id == span_id
        # Data from event
        assert record.model == "gpt-4o"
        assert record.input_tokens == 150
        assert record.agent_key == "chat"
        # Time from event, not fabricated (5.3)
        assert record.started_at_utc == _ts(0)
        assert record.completed_at_utc == _ts(1)

    def test_real_llm_failed_event(self, projector: CostProjector):
        """CostProjector must work with real LLMCallFailed (5.4)."""
        run_id = uuid4().hex
        trace_id = uuid4().hex
        span_id = uuid4().hex[:16]
        event = LLMCallFailed(
            run_id=run_id,
            trace_id=trace_id,
            span_id=span_id,
            model="gpt-4o",
            provider="openai",
            error_code="TIMEOUT",
            error_message="request timeout",
            agent_key="chat",
            started_at=_ts(0),
            completed_at=_ts(1),
        )
        import asyncio
        asyncio.run(projector.handle(event))
        record = projector._publisher.submitted[0]
        assert record.run_id == run_id
        assert record.trace_id == trace_id
        assert record.span_id == span_id
        assert record.error_code == "TIMEOUT"
        assert record.input_tokens == 0
        assert record.estimated_cost == 0.0
