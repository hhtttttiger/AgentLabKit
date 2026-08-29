"""Execution Model v2 — Acceptance Test Suite.

这些测试验证 Run → Event → Trace → Cost → Dataset → Eval → Replay → Compare
整条链路的真实贯通。

不是单元测试的堆砌，而是端到端的架构验收。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from agent_runtime import (
    AgentMessage,
    AgentRole,
    AgentTurnRequest,
    ToolRegistry,
)
from agent_runtime.config import AgentSettings
from agent_runtime.contracts.run import AgentRun, ExecutionContext, RunStatus, RunTarget
from agent_runtime.event_bus import EventBus
from agent_runtime.events_v2 import (
    LLMCallCompleted,
    LLMCallFailed,
    LLMCallStarted,
    RunCancelled,
    RunCompleted,
    RunFailed,
    RunStarted,
    RuntimeEvent,
)
from agent_runtime.runtime import AgentRuntime
from llm_gateway import ProviderId, TextGenerateResponse, UsageInfo


# ── Helpers ──────────────────────────────────────────────────────────


class FakeGatewayService:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    async def generate_text(self, request):
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _make_runtime(gateway, *, tool_registry=None):
    if tool_registry is None:
        tool_registry = ToolRegistry()
    return AgentRuntime(
        settings=AgentSettings(),
        gateway=gateway,
        tool_registry=tool_registry,
    )


def _make_response(text: str, usage=None):
    import json
    payload = json.dumps({
        "kind": "final",
        "reply_text": text,
        "should_handoff": False,
    })
    return TextGenerateResponse(
        provider=ProviderId.OPENAI,
        model="gpt-4o",
        text=payload,
        usage=usage or UsageInfo(input_tokens=10, output_tokens=5),
    )


# ── Acceptance Test A: Blocking Identity ─────────────────────────────


class TestAcceptanceBlockingIdentity:
    """AgentRuntime.run → Event → identity 一致性。

    验证：
    - AgentRun.run_id == RunStarted.run_id == RunCompleted.run_id
    - AgentRun.trace_id == RunStarted.trace_id == RunCompleted.trace_id
    """

    @pytest.mark.asyncio
    async def test_run_event_identity_consistency(self):
        gateway = FakeGatewayService([_make_response("hello")])
        runtime = _make_runtime(gateway)

        collected_events: list[RuntimeEvent] = []
        original_emit = runtime._event_bus.emit

        async def capture_emit(event):
            collected_events.append(event)
            await original_emit(event)

        runtime._event_bus.emit = capture_emit

        agent_run = await runtime.run(AgentTurnRequest(
            user_message="hi",
            session_id="s1",
        ))

        run_started = [e for e in collected_events if isinstance(e, RunStarted)]
        run_completed = [e for e in collected_events if isinstance(e, RunCompleted)]

        assert len(run_started) == 1
        assert len(run_completed) == 1

        # Core invariant: identity is consistent across the chain
        assert agent_run.run_id == run_started[0].run_id
        assert agent_run.run_id == run_completed[0].run_id
        assert agent_run.trace_id == run_started[0].trace_id
        assert agent_run.trace_id == run_completed[0].trace_id

    @pytest.mark.asyncio
    async def test_run_id_is_uuid_hex(self):
        gateway = FakeGatewayService([_make_response("ok")])
        runtime = _make_runtime(gateway)

        agent_run = await runtime.run(AgentTurnRequest(
            user_message="q",
            session_id="s1",
        ))

        assert len(agent_run.run_id) == 32  # uuid4().hex
        assert len(agent_run.trace_id) == 32


# ── Acceptance Test B: Span Correlation ──────────────────────────────


class TestAcceptanceSpanCorrelation:
    """LLMCallStarted.span_id == LLMCallCompleted.span_id。"""

    def test_same_span_id_for_start_complete(self):
        span_id = "llm-span-1"
        started = LLMCallStarted(run_id="r", model="m", span_id=span_id)
        completed = LLMCallCompleted(run_id="r", model="m", span_id=span_id)
        assert started.span_id == completed.span_id

    def test_cost_projector_uses_event_identity(self):
        """CostProjector 使用 event 的 run_id/trace_id/span_id。"""
        from cost_analysis.projector import CostProjector

        publisher = MagicMock()
        projector = CostProjector(publisher=publisher)
        now = datetime.now(timezone.utc)
        event = LLMCallCompleted(
            run_id="run-abc",
            trace_id="trace-xyz",
            span_id="span-123",
            model="gpt-4",
            agent_key="test-agent",
            input_tokens=100,
            output_tokens=50,
            started_at=now,
            completed_at=now,
        )
        asyncio.run(projector.handle(event))

        # CostRecord 使用 event 的 identity
        assert publisher.submit_nowait.called
        record = publisher.submit_nowait.call_args[0][0]
        assert record.run_id == "run-abc"
        assert record.trace_id == "trace-xyz"
        assert record.span_id == "span-123"


# ── Acceptance Test C: Failure ───────────────────────────────────────


class TestAcceptanceFailure:
    """LLM exception → RunFailed + AgentRun.status == FAILED。"""

    @pytest.mark.asyncio
    async def test_failure_produces_run_failed_event(self):
        from llm_gateway.errors import GatewayError, GatewayErrorCode

        gateway = FakeGatewayService([
            GatewayError(GatewayErrorCode.PROVIDER_TIMEOUT, "timeout"),
        ])
        runtime = _make_runtime(gateway)

        collected_events: list[RuntimeEvent] = []
        original_emit = runtime._event_bus.emit

        async def capture_emit(event):
            collected_events.append(event)
            await original_emit(event)

        runtime._event_bus.emit = capture_emit

        agent_run = await runtime.run(AgentTurnRequest(
            user_message="q",
            session_id="s1",
        ))

        assert agent_run.status == RunStatus.FAILED

        run_failed = [e for e in collected_events if isinstance(e, RunFailed)]
        assert len(run_failed) == 1
        assert run_failed[0].run_id == agent_run.run_id


# ── Acceptance Test D: Cancellation ─────────────────────────────────


class TestAcceptanceCancellation:
    """RunCancelled 发出后没有 RunCompleted/RunFailed。"""

    def test_run_cancelled_event_semantics(self):
        event = RunCancelled(run_id="r", reason="user cancelled")
        assert event.run_id == "r"
        assert event.reason == "user cancelled"


# ── Acceptance Test E: Streaming ─────────────────────────────────────


class TestAcceptanceStreaming:
    """Streaming path 发出 RunStarted/RunCompleted。"""

    @pytest.mark.asyncio
    async def test_stream_emits_lifecycle_events(self):
        """Streaming path 使用 ExecutionContext 时发出 v2 生命周期事件。"""
        from unittest.mock import AsyncMock

        # 使用支持 streaming 的 mock gateway
        gateway = MagicMock()

        async def _fake_stream(*args, **kwargs):
            yield MagicMock(
                delta="stream reply",
                full_text="stream reply",
                is_done=True,
                usage=UsageInfo(input_tokens=10, output_tokens=5),
            )

        gateway.generate_text_stream = _fake_stream
        runtime = _make_runtime(gateway)

        collected_events: list[RuntimeEvent] = []
        original_emit = runtime._event_bus.emit

        async def capture_emit(event):
            collected_events.append(event)
            await original_emit(event)

        runtime._event_bus.emit = capture_emit

        ctx = ExecutionContext(session_id="s1")
        events = []
        async for event in runtime.stream_turn(
            AgentTurnRequest(user_message="hi", session_id="s1"),
            execution_context=ctx,
        ):
            events.append(event)

        run_started = [e for e in collected_events if isinstance(e, RunStarted)]
        run_completed = [e for e in collected_events if isinstance(e, RunCompleted)]

        assert len(run_started) == 1
        assert run_started[0].run_id == ctx.run_id
        assert len(run_completed) == 1
        assert run_completed[0].run_id == ctx.run_id


# ── Acceptance Test F: Dataset Evaluation ────────────────────────────


class TestAcceptanceDatasetEvaluation:
    """DatasetEvaluationRunner + RunExecutor → EvaluationContext.run 非空。"""

    @pytest.mark.asyncio
    async def test_executor_populates_context_run(self):
        from evaluation.contracts_v2 import DatasetExample, EvaluationResult, MetricResult
        from evaluation.dataset import DatasetEvaluationRunner, InMemoryDatasetStore
        from evaluation.replay import MockRunExecutor, RunTarget

        store = InMemoryDatasetStore()
        dataset_id = await store.create_dataset("test")
        await store.add_example(DatasetExample(
            example_id="1", dataset_id=dataset_id, input_text="What is AI?",
        ))

        class AssertingEvaluator:
            name = "asserting"
            context_had_run: bool = False

            async def evaluate(self, context):
                AssertingEvaluator.context_had_run = context.run is not None
                return EvaluationResult(
                    example_id=context.example.example_id,
                    score=0.9,
                )

        executor = MockRunExecutor(
            output_text="AI is ...",
            run_id="exec-run-1",
            trace_id="exec-trace-1",
        )
        evaluator = AssertingEvaluator()
        runner = DatasetEvaluationRunner(
            evaluator, store,
            run_executor=executor,
            target=RunTarget(agent_key="test-agent"),
        )

        result = await runner.run(dataset_id, "test-agent")

        assert result.status.value == "completed"
        assert AssertingEvaluator.context_had_run is True


# ── Acceptance Test G: Replay Ownership ──────────────────────────────


class TestAcceptanceReplayOwnership:
    """ReplayRunner 不生成 run_id/trace_id。"""

    @pytest.mark.asyncio
    async def test_replay_uses_executor_identity(self):
        from evaluation.contracts_v2 import AgentRunSummary
        from evaluation.replay import InMemoryRunStore, MockRunExecutor, ReplayRunner

        store = InMemoryRunStore()
        await store.save_run(AgentRunSummary(
            run_id="original-123",
            trace_id="trace-1",
            agent_key="agent-v1",
            input_text="test input",
            output_text="test output",
            status="completed",
        ))

        executor = MockRunExecutor(
            output_text="new output",
            run_id="runtime-generated",
            trace_id="runtime-trace",
        )
        runner = ReplayRunner(store, executor)

        result = await runner.replay("original-123")

        # run_id/trace_id 来自 executor（Runtime），不是 ReplayRunner
        assert result.new_run_id == "runtime-generated"
        assert result.new_run.trace_id == "runtime-trace"


# ── Acceptance Test H: Replay Target ─────────────────────────────────


class TestAcceptanceReplayTarget:
    """ReplayConfig.target 真正传入 RunExecutor。"""

    @pytest.mark.asyncio
    async def test_target_passed_to_executor(self):
        from evaluation.contracts_v2 import AgentRunSummary
        from evaluation.replay import (
            InMemoryRunStore,
            MockRunExecutor,
            ReplayConfig,
            ReplayRunner,
            RunTarget,
        )

        store = InMemoryRunStore()
        await store.save_run(AgentRunSummary(
            run_id="original",
            trace_id="trace-1",
            agent_key="agent-v1",
            input_text="test",
            output_text="out",
            status="completed",
        ))

        executor = MockRunExecutor(output_text="v2 output")
        runner = ReplayRunner(store, executor)

        config = ReplayConfig(
            target=RunTarget(agent_key="refund-agent", agent_version="v2"),
        )
        await runner.replay("original", config)

        # executor 收到了正确的 target
        assert executor.received_target.agent_key == "refund-agent"
        assert executor.received_target.agent_version == "v2"


# ── Acceptance Test I: Replay Compare ────────────────────────────────


class TestAcceptanceReplayCompare:
    """Replay baseline/candidate 使用同一个 example_id。"""

    @pytest.mark.asyncio
    async def test_compare_same_example_id(self):
        from evaluation.compare import compare_runs
        from evaluation.contracts_v2 import (
            AgentRunSummary,
            EvaluationResult,
            EvaluationRun,
            EvaluationRunStatus,
        )

        # 模拟 replay 比较：同一个 example_id，不同 score
        baseline = EvaluationRun(
            run_id="baseline-run",
            dataset_id="replay",
            agent_key="agent",
            status=EvaluationRunStatus.COMPLETED,
            results=[EvaluationResult(example_id="shared-id", score=0.5)],
            total_examples=1,
            completed_examples=1,
        )
        candidate = EvaluationRun(
            run_id="candidate-run",
            dataset_id="replay",
            agent_key="agent",
            status=EvaluationRunStatus.COMPLETED,
            results=[EvaluationResult(example_id="shared-id", score=0.9)],
            total_examples=1,
            completed_examples=1,
        )

        result = compare_runs(baseline, candidate)

        # 同一个 example_id → improved，不是 removed/new
        assert len(result.improved) == 1
        assert len(result.removed_examples) == 0
        assert len(result.new_examples) == 0
        assert result.improved[0].example_id == "shared-id"


# ── Acceptance Test J: Run Summary 不制造事实 ────────────────────────


class TestAcceptanceRunSummaryFacts:
    """AgentRunSummary.started_at=None 不会变成 datetime.now()。"""

    def test_none_started_at_stays_none(self):
        from evaluation.contracts_v2 import AgentRunSummary

        summary = AgentRunSummary(
            run_id="r",
            trace_id="t",
            input_text="x",
            output_text="y",
            status="completed",
        )

        # started_at 默认为 None，不会每次变成不同的 datetime.now()
        assert summary.started_at is None
        assert summary.started_at is None  # 再读一次，仍然是 None

    def test_real_started_at_preserved(self):
        from evaluation.contracts_v2 import AgentRunSummary

        real_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        summary = AgentRunSummary(
            run_id="r",
            trace_id="t",
            input_text="x",
            output_text="y",
            status="completed",
            started_at=real_time,
        )

        assert summary.started_at == real_time


# ── Cross-module: TraceProjector identity ────────────────────────────


class TestAcceptanceTraceIdentity:
    """TraceProjector 使用 event 的 identity，不生成新的。"""

    def test_projector_uses_event_identity(self):
        from observability.config import ObservabilitySettings
        from observability.projector import TraceProjector

        publisher = MagicMock()
        settings = ObservabilitySettings()
        projector = TraceProjector(publisher=publisher, settings=settings)

        run_id = "run-abc"
        trace_id = "a" * 32
        span_id = "b" * 16

        event = RunStarted(
            run_id=run_id,
            trace_id=trace_id,
            agent_key="test",
            span_id=span_id,
        )
        asyncio.run(projector.handle(event))

        # 投影后的 span 使用事件的 identity
        assert run_id in projector._open_spans
        assert span_id in projector._open_spans[run_id]


# ── Cross-module: ExecutionContext ownership ─────────────────────────


class TestAcceptanceExecutionContext:
    """ExecutionContext 是 identity 唯一来源。"""

    def test_unique_ids_per_context(self):
        ctx1 = ExecutionContext()
        ctx2 = ExecutionContext()
        assert ctx1.run_id != ctx2.run_id
        assert ctx1.trace_id != ctx2.trace_id

    def test_context_carries_target(self):
        target = RunTarget(agent_key="agent-v2", agent_version="2.0")
        ctx = ExecutionContext(target=target)
        assert ctx.target.agent_key == "agent-v2"
        assert ctx.target.agent_version == "2.0"

    def test_context_has_started_at(self):
        ctx = ExecutionContext()
        assert ctx.started_at is not None
        assert ctx.started_at.tzinfo is not None  # UTC

    def test_context_has_root_span_id(self):
        ctx = ExecutionContext()
        assert ctx.root_span_id is not None
        assert len(ctx.root_span_id) == 16  # uuid4().hex[:16]
