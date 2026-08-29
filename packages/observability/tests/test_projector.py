"""Tests for TraceProjector — RuntimeEvent v2 → Trace Projection."""

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


def _make_event(event_type: str, run_id: str = "", trace_id: str = "", **kwargs):
    ts = kwargs.pop("timestamp", _ts(0))
    return SimpleNamespace(
        event_type=event_type,
        event_id=uuid4().hex,
        run_id=run_id or uuid4().hex,
        trace_id=trace_id or uuid4().hex,
        span_id=uuid4().hex[:16],
        timestamp=ts,
        attributes={},
        **kwargs,
    )


@pytest.fixture()
def projector():
    return TraceProjector(FakePublisher(), _settings())


@pytest.fixture()
def run_ids():
    return uuid4().hex, uuid4().hex, uuid4().hex  # run_id, trace_id, span_id


# ── Run lifecycle ──────────────────────────────────────────────────


class TestRunLifecycle:
    def test_run_started_creates_root_span(self, projector: TraceProjector, run_ids):
        run_id, trace_id, _ = run_ids
        started = _make_event("run.started", run_id=run_id, trace_id=trace_id, agent_key="chat")
        import asyncio
        asyncio.run(projector.handle(started))
        assert run_id in projector._spans
        assert len(projector._spans[run_id]) == 1
        assert projector._spans[run_id][0].name == "agent.run"

    def test_run_completed_submits_envelope(self, projector: TraceProjector, run_ids):
        run_id, trace_id, _ = run_ids
        started = _make_event("run.started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0))
        completed = _make_event("run.completed", run_id=run_id, trace_id=trace_id, timestamp=_ts(1),
                                 total_input_tokens=100, total_output_tokens=50)
        import asyncio
        asyncio.run(projector.handle(started))
        asyncio.run(projector.handle(completed))
        assert len(projector._publisher.submitted) == 1
        env = projector._publisher.submitted[0]
        # TraceEnvelope normalizes run_id via UUID() (adds dashes)
        assert env.run_id == str(UUID(run_id))
        assert env.status == "ok"
        assert env.total_input_tokens == 100
        assert env.total_output_tokens == 50
        assert env.total_duration_ms >= 0

    def test_run_failed_submits_with_error_status(self, projector: TraceProjector, run_ids):
        run_id, trace_id, _ = run_ids
        started = _make_event("run.started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0))
        failed = _make_event("run.failed", run_id=run_id, trace_id=trace_id, timestamp=_ts(1),
                              error_code="PROVIDER_ERROR", error_message="model unavailable")
        import asyncio
        asyncio.run(projector.handle(started))
        asyncio.run(projector.handle(failed))
        assert len(projector._publisher.submitted) == 1
        assert projector._publisher.submitted[0].status == "error"

    def test_run_cancelled_submits_with_cancelled_status(self, projector: TraceProjector, run_ids):
        run_id, trace_id, _ = run_ids
        started = _make_event("run.started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0))
        cancelled = _make_event("run.cancelled", run_id=run_id, trace_id=trace_id, timestamp=_ts(1))
        import asyncio
        asyncio.run(projector.handle(started))
        asyncio.run(projector.handle(cancelled))
        assert projector._publisher.submitted[0].status == "cancelled"

    def test_run_started_then_completed_cleans_up_state(self, projector: TraceProjector, run_ids):
        run_id, trace_id, _ = run_ids
        started = _make_event("run.started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0))
        completed = _make_event("run.completed", run_id=run_id, trace_id=trace_id, timestamp=_ts(1))
        import asyncio
        asyncio.run(projector.handle(started))
        asyncio.run(projector.handle(completed))
        assert run_id not in projector._spans
        assert run_id not in projector._trace_ids
        assert run_id not in projector._run_meta

    def test_envelope_spans_sorted_by_time(self, projector: TraceProjector, run_ids):
        run_id, trace_id, _ = run_ids
        started = _make_event("run.started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0))
        llm_started = _make_event("llm.call_started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0),
                                   provider="openai", model="gpt-4o")
        llm_completed = _make_event("llm.call_completed", run_id=run_id, trace_id=trace_id, timestamp=_ts(1),
                                     input_tokens=100, output_tokens=50)
        completed = _make_event("run.completed", run_id=run_id, trace_id=trace_id, timestamp=_ts(2))
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
        run_id, trace_id, _ = run_ids
        started = _make_event("run.started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0))
        agent_s = _make_event("agent.started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0), agent_key="chat")
        agent_c = _make_event("agent.completed", run_id=run_id, trace_id=trace_id, timestamp=_ts(1))
        completed = _make_event("run.completed", run_id=run_id, trace_id=trace_id, timestamp=_ts(2))
        import asyncio
        for e in [started, agent_s, agent_c, completed]:
            asyncio.run(projector.handle(e))
        env = projector._publisher.submitted[0]
        agent_spans = [s for s in env.spans if s.name == "agent.process"]
        assert len(agent_spans) == 1
        assert agent_spans[0].duration_ms > 0

    def test_turn_started_completed_spans(self, projector: TraceProjector, run_ids):
        run_id, trace_id, _ = run_ids
        started = _make_event("run.started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0))
        turn_s = _make_event("agent.turn_started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0), turn_index=0)
        turn_c = _make_event("agent.turn_completed", run_id=run_id, trace_id=trace_id, timestamp=_ts(1), turn_index=0)
        completed = _make_event("run.completed", run_id=run_id, trace_id=trace_id, timestamp=_ts(2))
        import asyncio
        for e in [started, turn_s, turn_c, completed]:
            asyncio.run(projector.handle(e))
        env = projector._publisher.submitted[0]
        turn_spans = [s for s in env.spans if s.name == "agent.turn"]
        assert len(turn_spans) == 1


# ── LLM calls ─────────────────────────────────────────────────────


class TestLLMCalls:
    def test_llm_started_completed_spans_with_usage(self, projector: TraceProjector, run_ids):
        run_id, trace_id, _ = run_ids
        started = _make_event("run.started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0))
        llm_s = _make_event("llm.call_started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0),
                             provider="openai", model="gpt-4o")
        llm_c = _make_event("llm.call_completed", run_id=run_id, trace_id=trace_id, timestamp=_ts(1),
                             input_tokens=150, output_tokens=80, cache_write_tokens=10, cache_read_tokens=5,
                             estimated_cost=Decimal("0.002"))
        completed = _make_event("run.completed", run_id=run_id, trace_id=trace_id, timestamp=_ts(2))
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
        run_id, trace_id, _ = run_ids
        started = _make_event("run.started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0))
        llm_s = _make_event("llm.call_started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0),
                             provider="openai", model="gpt-4o")
        llm_f = _make_event("llm.call_failed", run_id=run_id, trace_id=trace_id, timestamp=_ts(1),
                             error_code="TIMEOUT", error_message="request timeout")
        completed = _make_event("run.completed", run_id=run_id, trace_id=trace_id, timestamp=_ts(2))
        import asyncio
        for e in [started, llm_s, llm_f, completed]:
            asyncio.run(projector.handle(e))
        env = projector._publisher.submitted[0]
        llm_spans = [s for s in env.spans if s.name == "llm.generate"]
        assert llm_spans[0].status == "error"


# ── Tool calls ─────────────────────────────────────────────────────


class TestToolCalls:
    def test_tool_started_completed_spans(self, projector: TraceProjector, run_ids):
        run_id, trace_id, _ = run_ids
        started = _make_event("run.started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0))
        tool_s = _make_event("tool.call_started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0),
                              tool_name="search", source_type="mcp")
        tool_c = _make_event("tool.call_completed", run_id=run_id, trace_id=trace_id, timestamp=_ts(1),
                              tool_name="search")
        completed = _make_event("run.completed", run_id=run_id, trace_id=trace_id, timestamp=_ts(2))
        import asyncio
        for e in [started, tool_s, tool_c, completed]:
            asyncio.run(projector.handle(e))
        env = projector._publisher.submitted[0]
        tool_spans = [s for s in env.spans if s.name == "tool.search"]
        assert len(tool_spans) == 1
        assert tool_spans[0].attributes["tool.name"] == "search"

    def test_tool_failed_closes_span_with_error(self, projector: TraceProjector, run_ids):
        run_id, trace_id, _ = run_ids
        started = _make_event("run.started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0))
        tool_s = _make_event("tool.call_started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0),
                              tool_name="calculate")
        tool_f = _make_event("tool.call_failed", run_id=run_id, trace_id=trace_id, timestamp=_ts(1),
                              tool_name="calculate", error_code="RUNTIME_ERROR", error_message="division by zero")
        completed = _make_event("run.completed", run_id=run_id, trace_id=trace_id, timestamp=_ts(2))
        import asyncio
        for e in [started, tool_s, tool_f, completed]:
            asyncio.run(projector.handle(e))
        env = projector._publisher.submitted[0]
        tool_spans = [s for s in env.spans if s.name == "tool.calculate"]
        assert tool_spans[0].status == "error"


# ── Guardrails ─────────────────────────────────────────────────────


class TestGuardrails:
    def test_guardrail_evaluated_span(self, projector: TraceProjector, run_ids):
        run_id, trace_id, _ = run_ids
        started = _make_event("run.started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0))
        gr = _make_event("guardrail.evaluated", run_id=run_id, trace_id=trace_id, timestamp=_ts(0),
                          guardrail_name="toxicity", guardrail_type="output", passed=True)
        completed = _make_event("run.completed", run_id=run_id, trace_id=trace_id, timestamp=_ts(1))
        import asyncio
        for e in [started, gr, completed]:
            asyncio.run(projector.handle(e))
        env = projector._publisher.submitted[0]
        gr_spans = [s for s in env.spans if "guardrail" in s.name]
        assert len(gr_spans) == 1
        assert gr_spans[0].attributes["guardrail.passed"] is True

    def test_guardrail_blocked_creates_error_span(self, projector: TraceProjector, run_ids):
        run_id, trace_id, _ = run_ids
        started = _make_event("run.started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0))
        gr = _make_event("guardrail.blocked", run_id=run_id, trace_id=trace_id, timestamp=_ts(0),
                          guardrail_name="toxicity", guardrail_type="output",
                          action="block", reason="toxic content detected")
        completed = _make_event("run.completed", run_id=run_id, trace_id=trace_id, timestamp=_ts(1))
        import asyncio
        for e in [started, gr, completed]:
            asyncio.run(projector.handle(e))
        env = projector._publisher.submitted[0]
        gr_spans = [s for s in env.spans if "guardrail" in s.name]
        assert gr_spans[0].status == "error"


# ── Multi-agent ────────────────────────────────────────────────────


class TestMultiAgent:
    def test_handoff_spans(self, projector: TraceProjector, run_ids):
        run_id, trace_id, _ = run_ids
        started = _make_event("run.started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0))
        ho_s = _make_event("handoff.started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0),
                            source_agent="planner", target_agent="coder", reason="need code generation")
        ho_c = _make_event("handoff.completed", run_id=run_id, trace_id=trace_id, timestamp=_ts(1))
        completed = _make_event("run.completed", run_id=run_id, trace_id=trace_id, timestamp=_ts(2))
        import asyncio
        for e in [started, ho_s, ho_c, completed]:
            asyncio.run(projector.handle(e))
        env = projector._publisher.submitted[0]
        ho_spans = [s for s in env.spans if s.name == "handoff"]
        assert len(ho_spans) == 1
        assert ho_spans[0].attributes["handoff.source"] == "planner"
        assert ho_spans[0].attributes["handoff.target"] == "coder"

    def test_delegation_spans(self, projector: TraceProjector, run_ids):
        run_id, trace_id, _ = run_ids
        started = _make_event("run.started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0))
        del_s = _make_event("delegation.started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0),
                             target_agent="coder", tool_name="delegate_to_coder")
        del_c = _make_event("delegation.completed", run_id=run_id, trace_id=trace_id, timestamp=_ts(1))
        completed = _make_event("run.completed", run_id=run_id, trace_id=trace_id, timestamp=_ts(2))
        import asyncio
        for e in [started, del_s, del_c, completed]:
            asyncio.run(projector.handle(e))
        env = projector._publisher.submitted[0]
        del_spans = [s for s in env.spans if s.name == "delegation"]
        assert len(del_spans) == 1


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
        assert len(projector._spans) == 0

    def test_max_spans_per_trace_limit(self, projector: TraceProjector, run_ids):
        run_id, trace_id, _ = run_ids
        projector._settings = ObservabilitySettings(max_spans_per_trace=3)
        import asyncio
        asyncio.run(projector.handle(_make_event("run.started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0))))
        for i in range(10):
            asyncio.run(projector.handle(_make_event("agent.started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0))))
        assert len(projector._spans[run_id]) <= 3  # root + 2 more

    def test_duration_calculation(self, projector: TraceProjector, run_ids):
        run_id, trace_id, _ = run_ids
        started = _make_event("run.started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0))
        completed = _make_event("run.completed", run_id=run_id, trace_id=trace_id, timestamp=_ts(1))
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
        run_id, trace_id, _ = run_ids
        started = _make_event("run.started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0))
        completed = _make_event("run.completed", run_id=run_id, trace_id=trace_id, timestamp=_ts(1))
        import asyncio
        asyncio.run(projector.handle(started))
        asyncio.run(projector.handle(completed))  # should not raise

    def test_multiple_runs_independent(self, projector: TraceProjector):
        r1, t1 = uuid4().hex, uuid4().hex
        r2, t2 = uuid4().hex, uuid4().hex
        import asyncio
        asyncio.run(projector.handle(_make_event("run.started", run_id=r1, trace_id=t1, timestamp=_ts(0))))
        asyncio.run(projector.handle(_make_event("run.started", run_id=r2, trace_id=t2, timestamp=_ts(0))))
        assert r1 in projector._spans
        assert r2 in projector._spans
        assert projector._spans[r1] is not projector._spans[r2]

    def test_parent_span_id_chain(self, projector: TraceProjector, run_ids):
        run_id, trace_id, _ = run_ids
        import asyncio
        asyncio.run(projector.handle(_make_event("run.started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0))))
        asyncio.run(projector.handle(_make_event("agent.started", run_id=run_id, trace_id=trace_id, timestamp=_ts(0))))
        spans = projector._spans[run_id]
        assert spans[1].parent_span_id == spans[0].span_id  # agent -> run
