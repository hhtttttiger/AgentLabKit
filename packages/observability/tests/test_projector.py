"""Tests for TraceProjector — RuntimeEvent v2 → Trace Projection.

Phase 4 rewrite: projector is pure projection. span_id / parent_span_id
come from events (Runtime is sole creator). No inference.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from queue import Queue
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from observability.config import ObservabilitySettings
from observability.contracts import TraceEnvelope
from observability.projector import TraceProjector


class FakePublisher:
    """收集 submit_nowait 调用的 fake publisher。"""

    def __init__(self) -> None:
        self.submitted: list[TraceEnvelope] = []

    def submit_nowait(self, envelope: TraceEnvelope) -> None:
        self.submitted.append(envelope)


def _settings(**overrides) -> ObservabilitySettings:
    return ObservabilitySettings(**overrides)


def _ts(minutes: int = 0) -> datetime:
    return datetime(2026, 8, 28, 12, minutes, 0, tzinfo=timezone.utc)


def _make_event(
    event_type: str,
    run_id: str = "",
    trace_id: str = "",
    span_id: str | None = None,
    parent_span_id: str | None = None,
    **kwargs,
):
    """Create a mock RuntimeEvent with all required identity fields."""
    ts = kwargs.pop("timestamp", _ts(0))
    return SimpleNamespace(
        event_type=event_type,
        event_id=uuid4().hex,
        run_id=run_id or uuid4().hex,
        trace_id=trace_id or uuid4().hex,
        span_id=span_id or uuid4().hex[:16],
        parent_span_id=parent_span_id,
        timestamp=ts,
        attributes={},
        **kwargs,
    )


@pytest.fixture()
def projector():
    return TraceProjector(FakePublisher(), _settings())


@pytest.fixture()
def run_ids():
    """Generate a consistent set of run_id, trace_id, root_span_id."""
    return uuid4().hex, uuid4().hex, uuid4().hex[:16]


# ── Run lifecycle ──────────────────────────────────────────────────


class TestRunLifecycle:
    def test_run_started_creates_root_span(self, projector: TraceProjector, run_ids):
        run_id, trace_id, root_span_id = run_ids
        started = _make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, agent_key="chat",
        )
        import asyncio
        asyncio.run(projector.handle(started))
        # Root span is in open_spans until finalized
        assert run_id in projector._open_spans
        assert root_span_id in projector._open_spans[run_id]
        assert projector._open_spans[run_id][root_span_id].name == "agent.run"

    def test_run_completed_submits_envelope(self, projector: TraceProjector, run_ids):
        run_id, trace_id, root_span_id = run_ids
        started = _make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(0),
        )
        completed = _make_event(
            "run.completed", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(1),
            total_input_tokens=100, total_output_tokens=50,
        )
        import asyncio
        asyncio.run(projector.handle(started))
        asyncio.run(projector.handle(completed))
        assert len(projector._publisher.submitted) == 1
        env = projector._publisher.submitted[0]
        assert env.run_id == str(UUID(run_id))
        assert env.status == "ok"
        assert env.total_input_tokens == 100
        assert env.total_output_tokens == 50
        assert env.total_duration_ms >= 0

    def test_run_failed_submits_with_error_status(self, projector: TraceProjector, run_ids):
        run_id, trace_id, root_span_id = run_ids
        started = _make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(0),
        )
        failed = _make_event(
            "run.failed", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(1),
            error_code="PROVIDER_ERROR", error_message="model unavailable",
        )
        import asyncio
        asyncio.run(projector.handle(started))
        asyncio.run(projector.handle(failed))
        assert len(projector._publisher.submitted) == 1
        assert projector._publisher.submitted[0].status == "error"

    def test_run_cancelled_submits_with_cancelled_status(self, projector: TraceProjector, run_ids):
        run_id, trace_id, root_span_id = run_ids
        started = _make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(0),
        )
        cancelled = _make_event(
            "run.cancelled", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(1),
        )
        import asyncio
        asyncio.run(projector.handle(started))
        asyncio.run(projector.handle(cancelled))
        assert projector._publisher.submitted[0].status == "cancelled"

    def test_run_started_then_completed_cleans_up_state(self, projector: TraceProjector, run_ids):
        run_id, trace_id, root_span_id = run_ids
        started = _make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(0),
        )
        completed = _make_event(
            "run.completed", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(1),
        )
        import asyncio
        asyncio.run(projector.handle(started))
        asyncio.run(projector.handle(completed))
        assert run_id not in projector._spans
        assert run_id not in projector._trace_ids
        assert run_id not in projector._run_meta
        assert run_id not in projector._open_spans

    def test_envelope_spans_sorted_by_time(self, projector: TraceProjector, run_ids):
        run_id, trace_id, root_span_id = run_ids
        llm_span_id = uuid4().hex[:16]
        started = _make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(0),
        )
        llm_started = _make_event(
            "llm.call_started", run_id=run_id, trace_id=trace_id,
            span_id=llm_span_id, parent_span_id=root_span_id, timestamp=_ts(0),
            provider="openai", model="gpt-4o",
        )
        llm_completed = _make_event(
            "llm.call_completed", run_id=run_id, trace_id=trace_id,
            span_id=llm_span_id, timestamp=_ts(1),
            input_tokens=100, output_tokens=50,
        )
        completed = _make_event(
            "run.completed", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(2),
        )
        import asyncio
        asyncio.run(projector.handle(started))
        asyncio.run(projector.handle(llm_started))
        asyncio.run(projector.handle(llm_completed))
        asyncio.run(projector.handle(completed))
        env = projector._publisher.submitted[0]
        times = [s.started_at_utc for s in env.spans]
        assert times == sorted(times)


# ── Agent lifecycle ────────────────────────────────────────────────


class TestAgentLifecycle:
    def test_agent_started_completed_spans(self, projector: TraceProjector, run_ids):
        run_id, trace_id, root_span_id = run_ids
        agent_span_id = uuid4().hex[:16]
        started = _make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(0),
        )
        agent_s = _make_event(
            "agent.started", run_id=run_id, trace_id=trace_id,
            span_id=agent_span_id, parent_span_id=root_span_id, timestamp=_ts(0),
            agent_key="chat",
        )
        agent_c = _make_event(
            "agent.completed", run_id=run_id, trace_id=trace_id,
            span_id=agent_span_id, timestamp=_ts(1),
        )
        completed = _make_event(
            "run.completed", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(2),
        )
        import asyncio
        for e in [started, agent_s, agent_c, completed]:
            asyncio.run(projector.handle(e))
        env = projector._publisher.submitted[0]
        agent_spans = [s for s in env.spans if s.name == "agent.process"]
        assert len(agent_spans) == 1
        assert agent_spans[0].duration_ms > 0
        # parent comes from event, not inferred
        assert agent_spans[0].parent_span_id == root_span_id

    def test_turn_started_completed_spans(self, projector: TraceProjector, run_ids):
        run_id, trace_id, root_span_id = run_ids
        turn_span_id = uuid4().hex[:16]
        started = _make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(0),
        )
        turn_s = _make_event(
            "agent.turn_started", run_id=run_id, trace_id=trace_id,
            span_id=turn_span_id, parent_span_id=root_span_id, timestamp=_ts(0),
            turn_index=0,
        )
        turn_c = _make_event(
            "agent.turn_completed", run_id=run_id, trace_id=trace_id,
            span_id=turn_span_id, timestamp=_ts(1),
            turn_index=0,
        )
        completed = _make_event(
            "run.completed", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(2),
        )
        import asyncio
        for e in [started, turn_s, turn_c, completed]:
            asyncio.run(projector.handle(e))
        env = projector._publisher.submitted[0]
        turn_spans = [s for s in env.spans if s.name == "agent.turn"]
        assert len(turn_spans) == 1


# ── LLM calls ─────────────────────────────────────────────────────


class TestLLMCalls:
    def test_llm_started_completed_spans_with_usage(self, projector: TraceProjector, run_ids):
        run_id, trace_id, root_span_id = run_ids
        llm_span_id = uuid4().hex[:16]
        started = _make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(0),
        )
        llm_s = _make_event(
            "llm.call_started", run_id=run_id, trace_id=trace_id,
            span_id=llm_span_id, parent_span_id=root_span_id, timestamp=_ts(0),
            provider="openai", model="gpt-4o",
        )
        llm_c = _make_event(
            "llm.call_completed", run_id=run_id, trace_id=trace_id,
            span_id=llm_span_id, timestamp=_ts(1),
            input_tokens=150, output_tokens=80, cache_write_tokens=10,
            cache_read_tokens=5, estimated_cost=Decimal("0.002"),
        )
        completed = _make_event(
            "run.completed", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(2),
        )
        import asyncio
        for e in [started, llm_s, llm_c, completed]:
            asyncio.run(projector.handle(e))
        env = projector._publisher.submitted[0]
        llm_spans = [s for s in env.spans if s.name == "llm.generate"]
        assert len(llm_spans) == 1
        attrs = llm_spans[0].attributes
        assert attrs["gen_ai.usage.input_tokens"] == 150
        assert attrs["gen_ai.usage.output_tokens"] == 80
        assert attrs["gen_ai.request.model"] == "gpt-4o"

    def test_llm_failed_closes_span_with_error(self, projector: TraceProjector, run_ids):
        run_id, trace_id, root_span_id = run_ids
        llm_span_id = uuid4().hex[:16]
        started = _make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(0),
        )
        llm_s = _make_event(
            "llm.call_started", run_id=run_id, trace_id=trace_id,
            span_id=llm_span_id, parent_span_id=root_span_id, timestamp=_ts(0),
            provider="openai", model="gpt-4o",
        )
        llm_f = _make_event(
            "llm.call_failed", run_id=run_id, trace_id=trace_id,
            span_id=llm_span_id, timestamp=_ts(1),
            error_code="TIMEOUT", error_message="request timeout",
        )
        completed = _make_event(
            "run.completed", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(2),
        )
        import asyncio
        for e in [started, llm_s, llm_f, completed]:
            asyncio.run(projector.handle(e))
        env = projector._publisher.submitted[0]
        llm_spans = [s for s in env.spans if s.name == "llm.generate"]
        assert llm_spans[0].status == "error"


# ── Tool calls ─────────────────────────────────────────────────────


class TestToolCalls:
    def test_tool_started_completed_spans(self, projector: TraceProjector, run_ids):
        run_id, trace_id, root_span_id = run_ids
        tool_span_id = uuid4().hex[:16]
        started = _make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(0),
        )
        tool_s = _make_event(
            "tool.call_started", run_id=run_id, trace_id=trace_id,
            span_id=tool_span_id, parent_span_id=root_span_id, timestamp=_ts(0),
            tool_name="search", source_type="mcp",
        )
        tool_c = _make_event(
            "tool.call_completed", run_id=run_id, trace_id=trace_id,
            span_id=tool_span_id, timestamp=_ts(1),
            tool_name="search", result="found 3 results", is_error=False,
        )
        completed = _make_event(
            "run.completed", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(2),
        )
        import asyncio
        for e in [started, tool_s, tool_c, completed]:
            asyncio.run(projector.handle(e))
        env = projector._publisher.submitted[0]
        tool_spans = [s for s in env.spans if s.name == "tool.search"]
        assert len(tool_spans) == 1
        assert tool_spans[0].attributes["tool.name"] == "search"
        assert tool_spans[0].status == "ok"

    def test_tool_business_error_is_error_span(self, projector: TraceProjector, run_ids):
        """ToolCallCompleted(is_error=True) → error span (2.4)."""
        run_id, trace_id, root_span_id = run_ids
        tool_span_id = uuid4().hex[:16]
        started = _make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(0),
        )
        tool_s = _make_event(
            "tool.call_started", run_id=run_id, trace_id=trace_id,
            span_id=tool_span_id, parent_span_id=root_span_id, timestamp=_ts(0),
            tool_name="payment",
        )
        tool_c = _make_event(
            "tool.call_completed", run_id=run_id, trace_id=trace_id,
            span_id=tool_span_id, timestamp=_ts(1),
            tool_name="payment", result="insufficient funds", is_error=True,
        )
        completed = _make_event(
            "run.completed", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(2),
        )
        import asyncio
        for e in [started, tool_s, tool_c, completed]:
            asyncio.run(projector.handle(e))
        env = projector._publisher.submitted[0]
        tool_spans = [s for s in env.spans if s.name == "tool.payment"]
        assert tool_spans[0].status == "error"

    def test_tool_failed_closes_span_with_error(self, projector: TraceProjector, run_ids):
        run_id, trace_id, root_span_id = run_ids
        tool_span_id = uuid4().hex[:16]
        started = _make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(0),
        )
        tool_s = _make_event(
            "tool.call_started", run_id=run_id, trace_id=trace_id,
            span_id=tool_span_id, parent_span_id=root_span_id, timestamp=_ts(0),
            tool_name="calculate",
        )
        tool_f = _make_event(
            "tool.call_failed", run_id=run_id, trace_id=trace_id,
            span_id=tool_span_id, timestamp=_ts(1),
            tool_name="calculate", error_code="RUNTIME_ERROR",
            error_message="division by zero",
        )
        completed = _make_event(
            "run.completed", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(2),
        )
        import asyncio
        for e in [started, tool_s, tool_f, completed]:
            asyncio.run(projector.handle(e))
        env = projector._publisher.submitted[0]
        tool_spans = [s for s in env.spans if s.name == "tool.calculate"]
        assert tool_spans[0].status == "error"


# ── Guardrails ─────────────────────────────────────────────────────


class TestGuardrails:
    def test_guardrail_evaluated_span(self, projector: TraceProjector, run_ids):
        run_id, trace_id, root_span_id = run_ids
        gr_span_id = uuid4().hex[:16]
        started = _make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(0),
        )
        gr = _make_event(
            "guardrail.evaluated", run_id=run_id, trace_id=trace_id,
            span_id=gr_span_id, parent_span_id=root_span_id, timestamp=_ts(0),
            guardrail_name="toxicity", guardrail_type="output", passed=True,
        )
        completed = _make_event(
            "run.completed", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(1),
        )
        import asyncio
        for e in [started, gr, completed]:
            asyncio.run(projector.handle(e))
        env = projector._publisher.submitted[0]
        gr_spans = [s for s in env.spans if "guardrail" in s.name]
        assert len(gr_spans) == 1
        assert gr_spans[0].attributes["guardrail.passed"] is True

    def test_guardrail_blocked_enriches_evaluation_span(self, projector: TraceProjector, run_ids):
        run_id, trace_id, root_span_id = run_ids
        gr_span_id = uuid4().hex[:16]
        events = [
            _make_event("run.started", run_id=run_id, trace_id=trace_id,
                        span_id=root_span_id, timestamp=_ts(0)),
            _make_event("guardrail.evaluated", run_id=run_id, trace_id=trace_id,
                        span_id=gr_span_id, parent_span_id=root_span_id,
                        timestamp=_ts(0), guardrail_name="toxicity",
                        guardrail_type="output", passed=False),
            _make_event("guardrail.blocked", run_id=run_id, trace_id=trace_id,
                        span_id=gr_span_id, parent_span_id=root_span_id,
                        timestamp=_ts(0), guardrail_name="toxicity",
                        guardrail_type="output", action="block",
                        reason="policy"),
            _make_event("run.completed", run_id=run_id, trace_id=trace_id,
                        span_id=root_span_id, timestamp=_ts(1)),
        ]
        import asyncio
        for event in events:
            asyncio.run(projector.handle(event))
        env = projector._publisher.submitted[0]
        guardrail_spans = [s for s in env.spans if s.kind == "GUARDRAIL"]
        assert len(guardrail_spans) == 1
        assert guardrail_spans[0].span_id == gr_span_id
        assert guardrail_spans[0].status == "ok"
        assert guardrail_spans[0].attributes["guardrail.blocked"] is True
        assert guardrail_spans[0].attributes["guardrail.reason"] == "policy"
        span_ids = [span.span_id for span in env.spans]
        assert len(span_ids) == len(set(span_ids))


# ── Multi-agent ────────────────────────────────────────────────────


class TestMultiAgent:
    def test_handoff_spans(self, projector: TraceProjector, run_ids):
        run_id, trace_id, root_span_id = run_ids
        ho_span_id = uuid4().hex[:16]
        started = _make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(0),
        )
        ho_s = _make_event(
            "handoff.started", run_id=run_id, trace_id=trace_id,
            span_id=ho_span_id, parent_span_id=root_span_id, timestamp=_ts(0),
            source_agent="planner", target_agent="coder",
            reason="need code generation",
        )
        ho_c = _make_event(
            "handoff.completed", run_id=run_id, trace_id=trace_id,
            span_id=ho_span_id, timestamp=_ts(1),
        )
        completed = _make_event(
            "run.completed", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(2),
        )
        import asyncio
        for e in [started, ho_s, ho_c, completed]:
            asyncio.run(projector.handle(e))
        env = projector._publisher.submitted[0]
        ho_spans = [s for s in env.spans if s.name == "handoff"]
        assert len(ho_spans) == 1
        assert ho_spans[0].attributes["handoff.source"] == "planner"
        assert ho_spans[0].attributes["handoff.target"] == "coder"

    def test_delegation_spans(self, projector: TraceProjector, run_ids):
        run_id, trace_id, root_span_id = run_ids
        del_span_id = uuid4().hex[:16]
        started = _make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(0),
        )
        del_s = _make_event(
            "delegation.started", run_id=run_id, trace_id=trace_id,
            span_id=del_span_id, parent_span_id=root_span_id, timestamp=_ts(0),
            target_agent="coder", tool_name="delegate_to_coder",
        )
        del_c = _make_event(
            "delegation.completed", run_id=run_id, trace_id=trace_id,
            span_id=del_span_id, timestamp=_ts(1),
        )
        completed = _make_event(
            "run.completed", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(2),
        )
        import asyncio
        for e in [started, del_s, del_c, completed]:
            asyncio.run(projector.handle(e))
        env = projector._publisher.submitted[0]
        del_spans = [s for s in env.spans if s.name == "delegation"]
        assert len(del_spans) == 1


# ── SpanKind mapping ───────────────────────────────────────────────


class TestSpanKind:
    def test_llm_span_has_llm_call_kind(self, projector: TraceProjector, run_ids):
        run_id, trace_id, root_span_id = run_ids
        llm_span_id = uuid4().hex[:16]
        import asyncio
        asyncio.run(projector.handle(_make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(0),
        )))
        asyncio.run(projector.handle(_make_event(
            "llm.call_started", run_id=run_id, trace_id=trace_id,
            span_id=llm_span_id, parent_span_id=root_span_id, timestamp=_ts(0),
        )))
        asyncio.run(projector.handle(_make_event(
            "llm.call_completed", run_id=run_id, trace_id=trace_id,
            span_id=llm_span_id, timestamp=_ts(1),
        )))
        asyncio.run(projector.handle(_make_event(
            "run.completed", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(2),
        )))
        env = projector._publisher.submitted[0]
        llm_spans = [s for s in env.spans if s.name == "llm.generate"]
        assert llm_spans[0].kind == "LLM_CALL"

    def test_tool_span_has_tool_call_kind(self, projector: TraceProjector, run_ids):
        run_id, trace_id, root_span_id = run_ids
        tool_span_id = uuid4().hex[:16]
        import asyncio
        asyncio.run(projector.handle(_make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(0),
        )))
        asyncio.run(projector.handle(_make_event(
            "tool.call_started", run_id=run_id, trace_id=trace_id,
            span_id=tool_span_id, parent_span_id=root_span_id, timestamp=_ts(0),
            tool_name="search",
        )))
        asyncio.run(projector.handle(_make_event(
            "tool.call_completed", run_id=run_id, trace_id=trace_id,
            span_id=tool_span_id, timestamp=_ts(1),
            tool_name="search",
        )))
        asyncio.run(projector.handle(_make_event(
            "run.completed", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(2),
        )))
        env = projector._publisher.submitted[0]
        tool_spans = [s for s in env.spans if "tool." in s.name]
        assert tool_spans[0].kind == "TOOL_CALL"


# ── Retrieval projection (4.6) ────────────────────────────────────


class TestRetrieval:
    def test_retrieval_started_completed_span(self, projector: TraceProjector, run_ids):
        run_id, trace_id, root_span_id = run_ids
        ret_span_id = uuid4().hex[:16]
        import asyncio
        asyncio.run(projector.handle(_make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(0),
        )))
        asyncio.run(projector.handle(_make_event(
            "retrieval.started", run_id=run_id, trace_id=trace_id,
            span_id=ret_span_id, parent_span_id=root_span_id, timestamp=_ts(0),
            query="what is AI?", source="vector_store",
        )))
        asyncio.run(projector.handle(_make_event(
            "retrieval.completed", run_id=run_id, trace_id=trace_id,
            span_id=ret_span_id, timestamp=_ts(1),
            result_count=5, duration_ms=120,
        )))
        asyncio.run(projector.handle(_make_event(
            "run.completed", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(2),
        )))
        env = projector._publisher.submitted[0]
        ret_spans = [s for s in env.spans if s.kind == "RETRIEVAL"]
        assert len(ret_spans) == 1
        assert ret_spans[0].attributes["retrieval.query"] == "what is AI?"
        assert ret_spans[0].attributes["retrieval.result_count"] == 5

    def test_retrieval_failed_span(self, projector: TraceProjector, run_ids):
        run_id, trace_id, root_span_id = run_ids
        ret_span_id = uuid4().hex[:16]
        import asyncio
        asyncio.run(projector.handle(_make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(0),
        )))
        asyncio.run(projector.handle(_make_event(
            "retrieval.started", run_id=run_id, trace_id=trace_id,
            span_id=ret_span_id, parent_span_id=root_span_id, timestamp=_ts(0),
            query="test", source="vector_store",
        )))
        asyncio.run(projector.handle(_make_event(
            "retrieval.failed", run_id=run_id, trace_id=trace_id,
            span_id=ret_span_id, timestamp=_ts(1),
            error_message="connection timeout",
        )))
        asyncio.run(projector.handle(_make_event(
            "run.completed", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(2),
        )))
        env = projector._publisher.submitted[0]
        ret_spans = [s for s in env.spans if s.kind == "RETRIEVAL"]
        assert ret_spans[0].status == "error"


# ── Edge cases ─────────────────────────────────────────────────────


class TestEdgeCases:
    def test_non_v2_event_ignored(self, projector: TraceProjector):
        """旧事件（无 event_type 属性）应被忽略。"""
        old_event = SimpleNamespace(name="agent_start", trace_id="t1")
        import asyncio
        asyncio.run(projector.handle(old_event))
        assert len(projector._spans) == 0

    def test_empty_run_id_ignored(self, projector: TraceProjector):
        event = SimpleNamespace(
            event_type="run.started",
            event_id=uuid4().hex,
            run_id="",
            trace_id=uuid4().hex,
            span_id=uuid4().hex[:16],
            timestamp=_ts(0),
            attributes={},
        )
        import asyncio
        asyncio.run(projector.handle(event))
        assert projector._malformed_event_count == 1

    def test_missing_span_id_counted_as_malformed(self, projector: TraceProjector):
        """Events without span_id are counted as malformed (4.9)."""
        event = SimpleNamespace(
            event_type="run.started",
            event_id=uuid4().hex,
            run_id=uuid4().hex,
            trace_id=uuid4().hex,
            span_id=None,
            timestamp=_ts(0),
            attributes={},
        )
        import asyncio
        asyncio.run(projector.handle(event))
        assert projector._malformed_event_count == 1

    def test_max_spans_per_trace_limit(self, projector: TraceProjector, run_ids):
        run_id, trace_id, root_span_id = run_ids
        projector._settings = ObservabilitySettings(max_spans_per_trace=3)
        import asyncio
        asyncio.run(projector.handle(_make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(0),
        )))
        for i in range(10):
            span_id = uuid4().hex[:16]
            asyncio.run(projector.handle(_make_event(
                "agent.started", run_id=run_id, trace_id=trace_id,
                span_id=span_id, parent_span_id=root_span_id, timestamp=_ts(0),
            )))
            asyncio.run(projector.handle(_make_event(
                "agent.completed", run_id=run_id, trace_id=trace_id,
                span_id=span_id, timestamp=_ts(0),
            )))
        # After finalization: root + 2 more (max_spans_per_trace=3)
        asyncio.run(projector.handle(_make_event(
            "run.completed", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(1),
        )))
        env = projector._publisher.submitted[0]
        assert env.span_count <= 3

    def test_duration_calculation(self, projector: TraceProjector, run_ids):
        run_id, trace_id, root_span_id = run_ids
        started = _make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(0),
        )
        completed = _make_event(
            "run.completed", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(1),
        )
        import asyncio
        asyncio.run(projector.handle(started))
        asyncio.run(projector.handle(completed))
        env = projector._publisher.submitted[0]
        assert env.total_duration_ms == 60000  # 1 minute

    def test_publisher_error_does_not_raise(self, projector: TraceProjector, run_ids):
        class BrokenPublisher:
            def submit_nowait(self, envelope):
                raise RuntimeError("queue full")

        projector._publisher = BrokenPublisher()
        run_id, trace_id, root_span_id = run_ids
        started = _make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(0),
        )
        completed = _make_event(
            "run.completed", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(1),
        )
        import asyncio
        asyncio.run(projector.handle(started))
        asyncio.run(projector.handle(completed))  # should not raise

    def test_multiple_runs_independent(self, projector: TraceProjector):
        r1, t1, s1 = uuid4().hex, uuid4().hex, uuid4().hex[:16]
        r2, t2, s2 = uuid4().hex, uuid4().hex, uuid4().hex[:16]
        import asyncio
        asyncio.run(projector.handle(_make_event(
            "run.started", run_id=r1, trace_id=t1, span_id=s1, timestamp=_ts(0),
        )))
        asyncio.run(projector.handle(_make_event(
            "run.started", run_id=r2, trace_id=t2, span_id=s2, timestamp=_ts(0),
        )))
        assert r1 in projector._open_spans
        assert r2 in projector._open_spans
        assert projector._open_spans[r1] is not projector._open_spans[r2]

    def test_parent_span_id_from_event(self, projector: TraceProjector, run_ids):
        """parent_span_id comes from event, not inferred (3.2)."""
        run_id, trace_id, root_span_id = run_ids
        agent_span_id = uuid4().hex[:16]
        import asyncio
        asyncio.run(projector.handle(_make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(0),
        )))
        asyncio.run(projector.handle(_make_event(
            "agent.started", run_id=run_id, trace_id=trace_id,
            span_id=agent_span_id, parent_span_id=root_span_id, timestamp=_ts(0),
        )))
        asyncio.run(projector.handle(_make_event(
            "agent.completed", run_id=run_id, trace_id=trace_id,
            span_id=agent_span_id, timestamp=_ts(1),
        )))
        asyncio.run(projector.handle(_make_event(
            "run.completed", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(2),
        )))
        env = projector._publisher.submitted[0]
        agent_spans = [s for s in env.spans if s.name == "agent.process"]
        assert agent_spans[0].parent_span_id == root_span_id

    def test_same_name_concurrent_spans(self, projector: TraceProjector, run_ids):
        """Same-name concurrent spans tracked by span_id, not name (Phase 15 Test 8)."""
        run_id, trace_id, root_span_id = run_ids
        tool_a_id = uuid4().hex[:16]
        tool_b_id = uuid4().hex[:16]
        import asyncio
        asyncio.run(projector.handle(_make_event(
            "run.started", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(0),
        )))
        # search#A start
        asyncio.run(projector.handle(_make_event(
            "tool.call_started", run_id=run_id, trace_id=trace_id,
            span_id=tool_a_id, parent_span_id=root_span_id, timestamp=_ts(0),
            tool_name="search",
        )))
        # search#B start
        asyncio.run(projector.handle(_make_event(
            "tool.call_started", run_id=run_id, trace_id=trace_id,
            span_id=tool_b_id, parent_span_id=root_span_id, timestamp=_ts(0),
            tool_name="search",
        )))
        # search#A finish
        asyncio.run(projector.handle(_make_event(
            "tool.call_completed", run_id=run_id, trace_id=trace_id,
            span_id=tool_a_id, timestamp=_ts(1),
            tool_name="search",
        )))
        # search#B finish
        asyncio.run(projector.handle(_make_event(
            "tool.call_completed", run_id=run_id, trace_id=trace_id,
            span_id=tool_b_id, timestamp=_ts(1),
            tool_name="search",
        )))
        asyncio.run(projector.handle(_make_event(
            "run.completed", run_id=run_id, trace_id=trace_id,
            span_id=root_span_id, timestamp=_ts(2),
        )))
        env = projector._publisher.submitted[0]
        search_spans = [s for s in env.spans if s.name == "tool.search"]
        assert len(search_spans) == 2
        # Each closed its own span (no cross-contamination)
        span_ids = {s.span_id for s in search_spans}
        assert tool_a_id in span_ids
        assert tool_b_id in span_ids
