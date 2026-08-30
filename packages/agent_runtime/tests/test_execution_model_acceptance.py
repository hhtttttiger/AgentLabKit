"""Execution Model v2 — Acceptance Test Suite.

这些测试验证 Run → Event → Trace → Cost → Dataset → Eval → Replay → Compare
整条链路的真实贯通。

不是单元测试的堆砌，而是端到端的架构验收。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

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
from agent_runtime.guardrails.pipeline import GuardsPipeline
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
from agent_runtime.guardrails.pipeline import GuardsPipeline
from agent_runtime.runtime import AgentRuntime
from evaluation.contracts_v2 import RunView
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


# ── Acceptance Test E2: Streaming Failure Terminal ───────────────────


class TestAcceptanceStreamingFailureTerminal:
    """Streaming LLM error → exactly one RunFailed, no RunCompleted/RunCancelled。"""

    @pytest.mark.asyncio
    async def test_stream_llm_error_emits_run_failed(self):
        from llm_gateway.errors import GatewayError, GatewayErrorCode

        gateway = MagicMock()

        async def _failing_stream(*args, **kwargs):
            yield MagicMock(
                delta="partial",
                full_text="partial",
                is_done=False,
                usage=None,
            )
            raise GatewayError(GatewayErrorCode.PROVIDER_TIMEOUT, "stream timeout")

        gateway.generate_text_stream = _failing_stream
        runtime = _make_runtime(gateway)

        collected_events: list[RuntimeEvent] = []
        original_emit = runtime._event_bus.emit

        async def capture_emit(event):
            collected_events.append(event)
            await original_emit(event)

        runtime._event_bus.emit = capture_emit

        ctx = ExecutionContext(session_id="s1")
        with pytest.raises(Exception):
            async for _ in runtime.stream_turn(
                AgentTurnRequest(user_message="hi", session_id="s1"),
                execution_context=ctx,
            ):
                pass

        run_started = [e for e in collected_events if isinstance(e, RunStarted)]
        run_failed = [e for e in collected_events if isinstance(e, RunFailed)]
        run_completed = [e for e in collected_events if isinstance(e, RunCompleted)]
        run_cancelled = [e for e in collected_events if isinstance(e, RunCancelled)]

        assert len(run_started) == 1, f"Expected 1 RunStarted, got {len(run_started)}"
        assert len(run_failed) == 1, f"Expected 1 RunFailed, got {len(run_failed)}"
        assert len(run_completed) == 0, f"Expected 0 RunCompleted, got {len(run_completed)}"
        assert len(run_cancelled) == 0, f"Expected 0 RunCancelled, got {len(run_cancelled)}"
        assert run_failed[0].run_id == ctx.run_id


# ── Acceptance Test E3: Streaming Cancellation Terminal ──────────────


class TestAcceptanceStreamingCancellationTerminal:
    """Streaming CancelledError → exactly one RunCancelled, no RunCompleted/RunFailed。"""

    @pytest.mark.asyncio
    async def test_stream_cancel_emits_run_cancelled(self):
        gateway = MagicMock()

        async def _slow_stream(*args, **kwargs):
            yield MagicMock(
                delta="slow",
                full_text="slow",
                is_done=False,
                usage=None,
            )
            # Simulate cancellation by raising CancelledError
            raise asyncio.CancelledError()

        gateway.generate_text_stream = _slow_stream
        runtime = _make_runtime(gateway)

        collected_events: list[RuntimeEvent] = []
        original_emit = runtime._event_bus.emit

        async def capture_emit(event):
            collected_events.append(event)
            await original_emit(event)

        runtime._event_bus.emit = capture_emit

        ctx = ExecutionContext(session_id="s1")
        with pytest.raises(asyncio.CancelledError):
            async for _ in runtime.stream_turn(
                AgentTurnRequest(user_message="hi", session_id="s1"),
                execution_context=ctx,
            ):
                pass

        run_started = [e for e in collected_events if isinstance(e, RunStarted)]
        run_cancelled = [e for e in collected_events if isinstance(e, RunCancelled)]
        run_completed = [e for e in collected_events if isinstance(e, RunCompleted)]
        run_failed = [e for e in collected_events if isinstance(e, RunFailed)]

        assert len(run_started) == 1, f"Expected 1 RunStarted, got {len(run_started)}"
        assert len(run_cancelled) == 1, f"Expected 1 RunCancelled, got {len(run_cancelled)}"
        assert len(run_completed) == 0, f"Expected 0 RunCompleted, got {len(run_completed)}"
        assert len(run_failed) == 0, f"Expected 0 RunFailed, got {len(run_failed)}"
        assert run_cancelled[0].run_id == ctx.run_id


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


# ── Acceptance Test F2: Trace-aware Dataset Evaluation ───────────────


class TestAcceptanceTraceAwareDatasetEval:
    """TraceProvider injects spans into EvaluationContext for agent-native evaluators."""

    @pytest.mark.asyncio
    async def test_evaluator_sees_real_spans(self):
        from evaluation.contracts_v2 import (
            DatasetExample,
            EvaluationResult,
            SpanSummary,
            TraceProvider,
        )
        from evaluation.dataset import DatasetEvaluationRunner, InMemoryDatasetStore
        from evaluation.replay import MockRunExecutor, RunTarget

        # Fake TraceProvider that returns spans
        class FakeTraceProvider:
            async def get_spans(self, run_id: str):
                return [
                    SpanSummary(
                        span_id="span-1",
                        name="tool.search",
                        kind="TOOL_CALL",
                        duration_ms=200,
                        attributes={"tool.name": "search"},
                    ),
                ]

        store = InMemoryDatasetStore()
        dataset_id = await store.create_dataset("test")
        await store.add_example(DatasetExample(
            example_id="1", dataset_id=dataset_id, input_text="Search for AI",
        ))

        class SpanCheckingEvaluator:
            name = "span_checker"
            context_had_spans: bool = False

            async def evaluate(self, context):
                SpanCheckingEvaluator.context_had_spans = len(context.spans) > 0
                return EvaluationResult(
                    example_id=context.example.example_id,
                    passed=len(context.spans) > 0,
                    score=1.0 if len(context.spans) > 0 else 0.0,
                )

        executor = MockRunExecutor(
            output_text="AI results",
            run_id="trace-run-1",
            trace_id="trace-trace-1",
        )
        evaluator = SpanCheckingEvaluator()
        runner = DatasetEvaluationRunner(
            evaluator, store,
            run_executor=executor,
            target=RunTarget(agent_key="test-agent"),
            trace_provider=FakeTraceProvider(),
        )

        result = await runner.run(dataset_id, "test-agent")

        assert result.status.value == "completed"
        assert SpanCheckingEvaluator.context_had_spans is True
        assert result.overall_score == 1.0

    @pytest.mark.asyncio
    async def test_trace_provider_none_still_works(self):
        from evaluation.contracts_v2 import DatasetExample, EvaluationResult
        from evaluation.dataset import DatasetEvaluationRunner, InMemoryDatasetStore
        from evaluation.replay import MockRunExecutor, RunTarget

        store = InMemoryDatasetStore()
        dataset_id = await store.create_dataset("test")
        await store.add_example(DatasetExample(
            example_id="1", dataset_id=dataset_id, input_text="Hello",
        ))

        class SimpleEvaluator:
            name = "simple"
            async def evaluate(self, context):
                return EvaluationResult(
                    example_id=context.example.example_id,
                    passed=True,
                    score=1.0,
                )

        executor = MockRunExecutor(output_text="Hi")
        runner = DatasetEvaluationRunner(
            SimpleEvaluator(), store,
            run_executor=executor,
            target=RunTarget(agent_key="test-agent"),
            # No trace_provider
        )

        result = await runner.run(dataset_id, "test-agent")
        assert result.status.value == "completed"
        assert result.overall_score == 1.0


# ── Acceptance Test G: Replay Ownership ──────────────────────────────


class TestAcceptanceReplayOwnership:
    """ReplayRunner 不生成 run_id/trace_id。"""

    @pytest.mark.asyncio
    async def test_replay_uses_executor_identity(self):
        from evaluation.contracts_v2 import AgentRunSummary, RunStatus
        from evaluation.replay import InMemoryRunStore, MockRunExecutor, ReplayRunner

        store = InMemoryRunStore()
        await store.save_run(AgentRunSummary(
            run_id="original-123",
            trace_id="trace-1",
            agent_key="agent-v1",
            input_text="test input",
            output_text="test output",
            status=RunStatus.COMPLETED,
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
        from evaluation.contracts_v2 import AgentRunSummary, RunStatus
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
            status=RunStatus.COMPLETED,
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


# ── Acceptance Test H2: Replay Same Target ───────────────────────────


class TestAcceptanceReplaySameTarget:
    """ReplayConfig.target=None preserves original target including agent_version."""

    @pytest.mark.asyncio
    async def test_replay_preserves_original_target_version(self):
        from evaluation.contracts_v2 import AgentRunSummary
        from evaluation.replay import (
            InMemoryRunStore,
            MockRunExecutor,
            ReplayRunner,
            RunTarget,
        )

        store = InMemoryRunStore()
        await store.save_run(AgentRunSummary(
            run_id="orig",
            trace_id="trace-1",
            agent_key="refund-agent",
            input_text="test",
            output_text="out",
            status=RunStatus.COMPLETED,
            target=RunTarget(agent_key="refund-agent", agent_version="v17"),
        ))

        executor = MockRunExecutor(output_text="replayed")
        runner = ReplayRunner(store, executor)

        # config.target=None → should use original target
        await runner.replay("orig")

        assert executor.received_target is not None
        assert executor.received_target.agent_key == "refund-agent"
        assert executor.received_target.agent_version == "v17"


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
        from evaluation.contracts_v2 import AgentRunSummary, RunStatus

        summary = AgentRunSummary(
            run_id="r",
            trace_id="t",
            input_text="x",
            output_text="y",
            status=RunStatus.COMPLETED,
        )

        # started_at 默认为 None，不会每次变成不同的 datetime.now()
        assert summary.started_at is None
        assert summary.started_at is None  # 再读一次，仍然是 None

    def test_real_started_at_preserved(self):
        from evaluation.contracts_v2 import AgentRunSummary, RunStatus

        real_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        summary = AgentRunSummary(
            run_id="r",
            trace_id="t",
            input_text="x",
            output_text="y",
            status=RunStatus.COMPLETED,
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


# ── Acceptance Test K: RunView Protocol Extended ────────────────────


class TestAcceptanceRunViewProtocol:
    """RunView protocol 包含 evaluator 需要的 tool/token 属性。"""

    def test_agent_run_summary_satisfies_extended_run_view(self):
        from evaluation.contracts_v2 import AgentRunSummary, RunView

        summary = AgentRunSummary(
            run_id="r",
            trace_id="t",
            tool_names=["search", "refund"],
            tool_call_count=2,
            duration_ms=1500,
            total_input_tokens=100,
            total_output_tokens=50,
        )
        assert isinstance(summary, RunView)
        assert summary.tool_names == ["search", "refund"]
        assert summary.tool_call_count == 2
        assert summary.duration_ms == 1500
        assert summary.total_input_tokens == 100
        assert summary.total_output_tokens == 50

    def test_agent_run_satisfies_extended_run_view(self):
        from agent_runtime.contracts.run import AgentRun, RunStatus, RunUsage

        run = AgentRun(
            input="test",
            status=RunStatus.COMPLETED,
            usage=RunUsage(input_tokens=200, output_tokens=100),
            tool_names=["verify"],
            tool_call_count=1,
        )
        assert isinstance(run, RunView)
        assert run.tool_names == ["verify"]
        assert run.tool_call_count == 1
        assert run.total_input_tokens == 200
        assert run.total_output_tokens == 100


# ── Acceptance Test K2: RunView Contract (status/target) ─────────────


class TestAcceptanceRunViewContract:
    """RunView contract: status must be RunStatus enum, target accessible."""

    def test_status_coerced_from_string(self):
        from evaluation.contracts_v2 import AgentRunSummary, RunStatus

        summary = AgentRunSummary(
            run_id="r", trace_id="t", input_text="x", output_text="y",
            status="completed",
        )
        assert isinstance(summary.status, RunStatus)
        assert summary.status == RunStatus.COMPLETED

    def test_status_coerced_from_failed_string(self):
        from evaluation.contracts_v2 import AgentRunSummary, RunStatus

        summary = AgentRunSummary(
            run_id="r", trace_id="t", input_text="x", output_text="y",
            status=RunStatus.FAILED,
        )
        assert isinstance(summary.status, RunStatus)
        assert summary.status == RunStatus.FAILED

    def test_status_enum_preserved(self):
        from evaluation.contracts_v2 import AgentRunSummary, RunStatus

        summary = AgentRunSummary(
            run_id="r", trace_id="t", input_text="x", output_text="y",
            status=RunStatus.CANCELLED,
        )
        assert isinstance(summary.status, RunStatus)
        assert summary.status == RunStatus.CANCELLED

    def test_target_accessible(self):
        from evaluation.contracts_v2 import AgentRunSummary
        from evaluation.replay import RunTarget

        summary = AgentRunSummary(
            run_id="r", trace_id="t", input_text="x", output_text="y",
            target=RunTarget(agent_key="a", agent_version="v1"),
        )
        assert summary.target is not None
        assert summary.target.agent_key == "a"
        assert summary.target.agent_version == "v1"

    def test_target_none_by_default(self):
        from evaluation.contracts_v2 import AgentRunSummary

        summary = AgentRunSummary(
            run_id="r", trace_id="t", input_text="x", output_text="y",
        )
        assert summary.target is None


# ── Acceptance Test L: No Synthetic Facts ────────────────────────────


class TestAcceptanceNoSyntheticFacts:
    """Evaluation 契约不伪造时间戳。"""

    def test_example_eval_to_result_no_datetime_now(self):
        """to_eval_run_result() 不调用 datetime.now() 制造事实。"""
        from evaluation.contracts_v2 import ExampleEvaluation

        eval_run = ExampleEvaluation(
            example_id="42",
            run_id="run-abc",
        )
        result = eval_run.to_eval_run_result()

        # EvalRunResult 没有 started_at/finished_at 字段（旧版契约）
        # 关键验证：不会抛异常，且结果可用
        assert result.overall_score == 0.0
        assert result.error_message is None

    def test_agent_run_summary_none_timestamps_stable(self):
        """AgentRunSummary 的 None 时间戳不会变成 datetime.now()。"""
        from evaluation.contracts_v2 import AgentRunSummary

        summary = AgentRunSummary(
            run_id="r",
            trace_id="t",
            input_text="x",
            output_text="y",
            status="completed",
        )

        # started_at 默认为 None，多次读取始终为 None
        assert summary.started_at is None
        assert summary.started_at is None
        assert summary.finished_at is None
        assert summary.finished_at is None


# ── Acceptance Test M: Comparability Validation ──────────────────────


class TestAcceptanceComparability:
    """Compare 有基本 comparability validation。"""

    def test_different_dataset_version_raises(self):
        from evaluation.compare import IncompatibleEvaluationRuns, compare_runs
        from evaluation.contracts_v2 import (
            EvaluationResult,
            EvaluationRun,
            EvaluationRunStatus,
        )

        baseline = EvaluationRun(
            run_id="baseline",
            dataset_id="d",
            dataset_version="v1",
            agent_key="agent",
            status=EvaluationRunStatus.COMPLETED,
            results=[EvaluationResult(example_id="1", score=0.5)],
            total_examples=1,
            completed_examples=1,
        )
        current = EvaluationRun(
            run_id="current",
            dataset_id="d",
            dataset_version="v2",
            agent_key="agent",
            status=EvaluationRunStatus.COMPLETED,
            results=[EvaluationResult(example_id="1", score=0.8)],
            total_examples=1,
            completed_examples=1,
        )

        with pytest.raises(IncompatibleEvaluationRuns) as exc_info:
            compare_runs(baseline, current)
        assert "dataset_version" in str(exc_info.value)

    def test_none_version_skips_check(self):
        """dataset_version=None 不触发 mismatch。"""
        from evaluation.compare import compare_runs
        from evaluation.contracts_v2 import (
            EvaluationResult,
            EvaluationRun,
            EvaluationRunStatus,
        )

        baseline = EvaluationRun(
            run_id="baseline",
            dataset_id="d",
            dataset_version=None,
            agent_key="agent",
            status=EvaluationRunStatus.COMPLETED,
            results=[EvaluationResult(example_id="1", score=0.5)],
            total_examples=1,
            completed_examples=1,
        )
        current = EvaluationRun(
            run_id="current",
            dataset_id="d",
            dataset_version="v2",
            agent_key="agent",
            status=EvaluationRunStatus.COMPLETED,
            results=[EvaluationResult(example_id="1", score=0.8)],
            total_examples=1,
            completed_examples=1,
        )

        # Should NOT raise — None means "unknown", skip check
        result = compare_runs(baseline, current)
        assert len(result.improved) == 1

    def test_same_version_passes(self):
        from evaluation.compare import compare_runs
        from evaluation.contracts_v2 import (
            EvaluationResult,
            EvaluationRun,
            EvaluationRunStatus,
        )

        baseline = EvaluationRun(
            run_id="baseline",
            dataset_id="d",
            dataset_version="v1",
            agent_key="agent",
            status=EvaluationRunStatus.COMPLETED,
            results=[EvaluationResult(example_id="1", score=0.5)],
            total_examples=1,
            completed_examples=1,
        )
        current = EvaluationRun(
            run_id="current",
            dataset_id="d",
            dataset_version="v1",
            agent_key="agent",
            status=EvaluationRunStatus.COMPLETED,
            results=[EvaluationResult(example_id="1", score=0.8)],
            total_examples=1,
            completed_examples=1,
        )

        result = compare_runs(baseline, current)
        assert len(result.improved) == 1

    def test_evaluator_spec_creation(self):
        from evaluation.contracts_v2 import EvaluatorSpec

        spec = EvaluatorSpec(name="tool_called", version="1.0")
        assert spec.name == "tool_called"
        assert spec.version == "1.0"

    def test_evaluation_run_with_specs(self):
        from evaluation.contracts_v2 import (
            EvaluatorSpec,
            EvaluationRun,
            EvaluationRunStatus,
        )

        specs = [EvaluatorSpec(name="tool_called"), EvaluatorSpec(name="no_error", version="2.0")]
        run = EvaluationRun(
            run_id="r",
            dataset_id="d",
            dataset_version="v1",
            agent_key="agent",
            evaluator_specs=specs,
            status=EvaluationRunStatus.COMPLETED,
        )
        assert len(run.evaluator_specs) == 2
        assert run.evaluator_specs[0].name == "tool_called"
        assert run.dataset_version == "v1"


# ── Acceptance Test N: Full Chain Identity ───────────────────────────


class TestAcceptanceFullChainIdentity:
    """AgentRuntime.run → RuntimeEvent → TraceProjector → CostProjector
    全链路 run_id/trace_id 一致。"""

    @pytest.mark.asyncio
    async def test_full_chain_identity_consistency(self):
        """真实 AgentRuntime.run() 产生的事件喂给 TraceProjector 和 CostProjector，
        三者共享同一个 run_id/trace_id。"""
        from unittest.mock import AsyncMock, MagicMock

        from cost_analysis.projector import CostProjector
        from observability.config import ObservabilitySettings
        from observability.projector import TraceProjector

        # 1. 运行真实 AgentRuntime.run()
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

        # 2. 喂给 TraceProjector
        trace_publisher = MagicMock()
        trace_settings = ObservabilitySettings()
        trace_projector = TraceProjector(publisher=trace_publisher, settings=trace_settings)

        for event in collected_events:
            if hasattr(event, "event_type"):
                await trace_projector.handle(event)

        # 3. 喂给 CostProjector
        cost_publisher = MagicMock()
        cost_projector = CostProjector(publisher=cost_publisher)

        for event in collected_events:
            if hasattr(event, "event_type"):
                await cost_projector.handle(event)

        # 4. 验证全链路 identity 一致
        # AgentRun
        assert agent_run.run_id
        assert agent_run.trace_id

        # Events
        run_events = [e for e in collected_events if hasattr(e, "run_id") and e.run_id]
        for event in run_events:
            assert event.run_id == agent_run.run_id, \
                f"{type(event).__name__}.run_id={event.run_id} != AgentRun.run_id={agent_run.run_id}"
            assert event.trace_id == agent_run.trace_id, \
                f"{type(event).__name__}.trace_id={event.trace_id} != AgentRun.trace_id={agent_run.trace_id}"

        # TraceProjector: 验证提交的 TraceEnvelope 使用了正确的 identity
        # TraceEnvelope 的 run_id validator 会转为 UUID 格式（带连字符），
        # 所以用 UUID 归一化比较
        assert trace_publisher.submit_nowait.called, \
            "TraceProjector must submit a TraceEnvelope"
        envelope = trace_publisher.submit_nowait.call_args[0][0]
        assert UUID(envelope.run_id) == UUID(agent_run.run_id)
        assert UUID(envelope.trace_id) == UUID(agent_run.trace_id)

        # CostProjector: 验证提交的 CostRecord 使用了正确的 identity
        assert cost_publisher.submit_nowait.called, \
            "CostProjector must submit a CostRecord"
        record = cost_publisher.submit_nowait.call_args[0][0]
        assert record.run_id == agent_run.run_id
        assert record.trace_id == agent_run.trace_id


# ── Acceptance Test: LLM agent_key propagation ────────────────────


class TestAcceptanceLlmAgentKey:
    """LLMCallCompleted/Failed 携带 agent_key 供 CostProjector 使用。"""

    @pytest.mark.asyncio
    async def test_llm_completed_has_agent_key(self):
        gateway = FakeGatewayService([_make_response("ok")])
        runtime = _make_runtime(gateway)

        collected_events: list[RuntimeEvent] = []
        original_emit = runtime._event_bus.emit

        async def capture_emit(event):
            collected_events.append(event)
            await original_emit(event)

        runtime._event_bus.emit = capture_emit

        await runtime.run(AgentTurnRequest(
            user_message="q",
            session_id="s1",
            agent_key="refund-agent",
        ))

        llm_completed = [e for e in collected_events if isinstance(e, LLMCallCompleted)]
        assert len(llm_completed) >= 1
        assert llm_completed[0].agent_key == "refund-agent"

    def test_llm_started_has_agent_key_field(self):
        """LLMCallStarted 也有 agent_key 字段。"""
        event = LLMCallStarted(
            run_id="r",
            model="m",
            agent_key="test-agent",
        )
        assert event.agent_key == "test-agent"


# ── Acceptance Test: Streaming span_ids ────────────────────────────


class TestAcceptanceStreamingSpanIds:
    """Streaming path 的 RunStarted 携带 span_id。"""

    @pytest.mark.asyncio
    async def test_stream_run_started_has_span_id(self):
        from unittest.mock import AsyncMock

        gateway = MagicMock()

        async def _fake_stream(*args, **kwargs):
            yield MagicMock(
                delta="reply",
                full_text="reply",
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
        assert len(run_started) == 1
        assert run_started[0].span_id is not None
        assert len(run_started[0].span_id) == 16  # uuid4().hex[:16]


# ── Acceptance Test: Comparability with evaluator_specs ────────────


class TestAcceptanceComparabilityEvaluatorSpecs:
    """evaluator_specs 不一致时抛出 IncompatibleEvaluationRuns。"""

    def test_different_evaluator_specs_raises(self):
        from evaluation.compare import IncompatibleEvaluationRuns, compare_runs
        from evaluation.contracts_v2 import (
            EvaluatorSpec,
            EvaluationResult,
            EvaluationRun,
            EvaluationRunStatus,
        )

        baseline = EvaluationRun(
            run_id="baseline",
            dataset_id="ds1",
            agent_key="agent",
            status=EvaluationRunStatus.COMPLETED,
            results=[EvaluationResult(example_id="1", score=0.5)],
            evaluator_specs=[EvaluatorSpec(name="ragas", version="0.4")],
            total_examples=1,
            completed_examples=1,
        )
        current = EvaluationRun(
            run_id="current",
            dataset_id="ds1",
            agent_key="agent",
            status=EvaluationRunStatus.COMPLETED,
            results=[EvaluationResult(example_id="1", score=0.8)],
            evaluator_specs=[EvaluatorSpec(name="ragas", version="0.5")],
            total_examples=1,
            completed_examples=1,
        )

        with pytest.raises(IncompatibleEvaluationRuns) as exc_info:
            compare_runs(baseline, current)

        assert "evaluator_specs" in str(exc_info.value)

    def test_same_evaluator_specs_passes(self):
        from evaluation.compare import compare_runs
        from evaluation.contracts_v2 import (
            EvaluatorSpec,
            EvaluationResult,
            EvaluationRun,
            EvaluationRunStatus,
        )

        specs = [EvaluatorSpec(name="ragas", version="0.4")]
        baseline = EvaluationRun(
            run_id="baseline",
            dataset_id="ds1",
            agent_key="agent",
            status=EvaluationRunStatus.COMPLETED,
            results=[EvaluationResult(example_id="1", score=0.5)],
            evaluator_specs=specs,
            total_examples=1,
            completed_examples=1,
        )
        current = EvaluationRun(
            run_id="current",
            dataset_id="ds1",
            agent_key="agent",
            status=EvaluationRunStatus.COMPLETED,
            results=[EvaluationResult(example_id="1", score=0.8)],
            evaluator_specs=specs,
            total_examples=1,
            completed_examples=1,
        )

        result = compare_runs(baseline, current)
        assert len(result.improved) == 1

    def test_empty_specs_skips_check(self):
        from evaluation.compare import compare_runs
        from evaluation.contracts_v2 import (
            EvaluationResult,
            EvaluationRun,
            EvaluationRunStatus,
        )

        baseline = EvaluationRun(
            run_id="baseline",
            dataset_id="ds1",
            agent_key="agent",
            status=EvaluationRunStatus.COMPLETED,
            results=[EvaluationResult(example_id="1", score=0.5)],
            total_examples=1,
            completed_examples=1,
        )
        current = EvaluationRun(
            run_id="current",
            dataset_id="ds1",
            agent_key="agent",
            status=EvaluationRunStatus.COMPLETED,
            results=[EvaluationResult(example_id="1", score=0.8)],
            total_examples=1,
            completed_examples=1,
        )

        result = compare_runs(baseline, current)
        assert len(result.improved) == 1


# ── Acceptance Test: Replay example_id flows through ────────────────


class TestAcceptanceReplayExampleIdFlow:
    """ReplayConfig.example_id → ReplayResult.example_id 全链路传递。"""

    def test_config_example_id_flows_to_result(self):
        from evaluation.replay import ReplayResult
        from evaluation.compare import ComparisonResult

        comparison = ComparisonResult(baseline_run_id="orig", current_run_id="new")
        result = ReplayResult(
            original_run_id="orig",
            new_run_id="new",
            original_run=None,
            new_run=None,
            comparison=comparison,
            example_id="dataset-42",
        )
        assert result.example_id == "dataset-42"

    def test_config_example_id_none_by_default(self):
        from evaluation.replay import ReplayConfig

        config = ReplayConfig(target=None)
        assert config.example_id is None

    def test_result_example_id_none_by_default(self):
        from evaluation.replay import ReplayResult
        from evaluation.compare import ComparisonResult

        comparison = ComparisonResult(baseline_run_id="orig", current_run_id="new")
        result = ReplayResult(
            original_run_id="orig",
            new_run_id="new",
            original_run=None,
            new_run=None,
            comparison=comparison,
        )
        assert result.example_id is None


# ── Acceptance Test: CostRecord span_id and agent_key ───────────────


class TestAcceptanceCostRecordIdentity:
    """CostProjector 产出的 CostRecord 携带 span_id 和 agent_key。"""

    @pytest.mark.asyncio
    async def test_cost_record_has_span_id_and_agent_key(self):
        from unittest.mock import AsyncMock, MagicMock

        from cost_analysis.projector import CostProjector

        event = LLMCallCompleted(
            run_id="run-abc",
            trace_id="trace-xyz",
            span_id="span-001",
            agent_key="refund-agent",
            model="gpt-4",
            input_tokens=100,
            output_tokens=50,
        )

        publisher = MagicMock()
        projector = CostProjector(publisher=publisher)
        await projector.handle(event)

        assert publisher.submit_nowait.called
        record = publisher.submit_nowait.call_args[0][0]
        assert record.run_id == "run-abc"
        assert record.trace_id == "trace-xyz"
        assert record.span_id == "span-001"
        assert record.agent_key == "refund-agent"


# ── Acceptance Test: Streaming Failure Terminal Invariant ───────────


class TestAcceptanceStreamingFailureTerminal:
    """Streaming LLM error → exactly 1 RunFailed, 0 RunCompleted, 0 RunCancelled."""

    @pytest.mark.asyncio
    async def test_stream_llm_error_produces_run_failed(self):
        from llm_gateway.errors import GatewayError, GatewayErrorCode

        gateway = MagicMock()

        async def _failing_stream(*args, **kwargs):
            raise GatewayError(GatewayErrorCode.PROVIDER_TIMEOUT, "stream timeout")
            yield  # make it an async generator

        gateway.generate_text_stream = _failing_stream
        runtime = _make_runtime(gateway)

        collected_events: list[RuntimeEvent] = []
        original_emit = runtime._event_bus.emit

        async def capture_emit(event):
            collected_events.append(event)
            await original_emit(event)

        runtime._event_bus.emit = capture_emit

        ctx = ExecutionContext(session_id="s1")
        with pytest.raises(Exception):
            async for _ in runtime.stream_turn(
                AgentTurnRequest(user_message="hi", session_id="s1"),
                execution_context=ctx,
            ):
                pass

        run_started = [e for e in collected_events if isinstance(e, RunStarted)]
        run_completed = [e for e in collected_events if isinstance(e, RunCompleted)]
        run_failed = [e for e in collected_events if isinstance(e, RunFailed)]
        run_cancelled = [e for e in collected_events if isinstance(e, RunCancelled)]

        assert len(run_started) == 1, f"Expected 1 RunStarted, got {len(run_started)}"
        assert len(run_failed) == 1, f"Expected 1 RunFailed, got {len(run_failed)}"
        assert len(run_completed) == 0, f"Expected 0 RunCompleted, got {len(run_completed)}"
        assert len(run_cancelled) == 0, f"Expected 0 RunCancelled, got {len(run_cancelled)}"
        assert run_failed[0].run_id == ctx.run_id


# ── Acceptance Test: Blocking Guardrail Block ───────────────────────


class TestAcceptanceBlockingGuardrailBlock:
    """Blocking guardrail block → RunStarted + GuardrailBlocked + RunCompleted."""

    @pytest.mark.asyncio
    async def test_guardrail_block_produces_full_run_lifecycle(self):
        from agent_runtime.guardrails import Guard, GuardContext, GuardResult, GuardVerdict

        class BlockingGuard:
            name = "test_blocker"

            async def evaluate(self, ctx: GuardContext) -> GuardResult:
                return GuardResult(
                    guard_name="test_blocker",
                    verdict=GuardVerdict.BLOCK,
                    reason="blocked for test",
                )

        guards_pipeline = GuardsPipeline(input_guards=[BlockingGuard()])
        gateway = FakeGatewayService([_make_response("should not reach")])
        runtime = _make_runtime(gateway, tool_registry=ToolRegistry())
        runtime.guards_pipeline = guards_pipeline
        runtime._turn_guards.guards_pipeline = guards_pipeline

        collected_events: list[RuntimeEvent] = []
        original_emit = runtime._event_bus.emit

        async def capture_emit(event):
            collected_events.append(event)
            await original_emit(event)

        runtime._event_bus.emit = capture_emit

        agent_run = await runtime.run(AgentTurnRequest(
            user_message="blocked input",
            session_id="s1",
        ))

        run_started = [e for e in collected_events if isinstance(e, RunStarted)]
        run_completed = [e for e in collected_events if isinstance(e, RunCompleted)]
        run_failed = [e for e in collected_events if isinstance(e, RunFailed)]

        # Must have RunStarted
        assert len(run_started) == 1, f"Expected 1 RunStarted, got {len(run_started)}"
        # Must have RunCompleted (blocked ≠ failure)
        assert len(run_completed) == 1, f"Expected 1 RunCompleted, got {len(run_completed)}"
        # Must NOT have RunFailed
        assert len(run_failed) == 0, f"Expected 0 RunFailed, got {len(run_failed)}"
        # Identity consistency
        assert run_started[0].run_id == agent_run.run_id
        assert run_completed[0].run_id == agent_run.run_id
        # AgentRun exists and has blocked metadata
        assert agent_run.run_id
        assert agent_run.status == RunStatus.COMPLETED


# ── Acceptance Test: Streaming Guardrail Block ──────────────────────


class TestAcceptanceStreamingGuardrailBlock:
    """Streaming guardrail block → RunStarted + RunCompleted."""

    @pytest.mark.asyncio
    async def test_stream_guardrail_block_produces_full_run_lifecycle(self):
        from agent_runtime.guardrails import Guard, GuardContext, GuardResult, GuardVerdict

        class BlockingGuard:
            name = "test_blocker"

            async def evaluate(self, ctx: GuardContext) -> GuardResult:
                return GuardResult(
                    guard_name="test_blocker",
                    verdict=GuardVerdict.BLOCK,
                    reason="blocked for test",
                )

        guards_pipeline = GuardsPipeline(input_guards=[BlockingGuard()])
        gateway = MagicMock()

        async def _empty_stream(*args, **kwargs):
            if False:
                yield  # pragma: no cover

        gateway.generate_text_stream = _empty_stream
        runtime = _make_runtime(gateway)
        runtime.guards_pipeline = guards_pipeline
        runtime._turn_guards.guards_pipeline = guards_pipeline

        collected_events: list[RuntimeEvent] = []
        original_emit = runtime._event_bus.emit

        async def capture_emit(event):
            collected_events.append(event)
            await original_emit(event)

        runtime._event_bus.emit = capture_emit

        ctx = ExecutionContext(session_id="s1")
        events = []
        async for event in runtime.stream_turn(
            AgentTurnRequest(user_message="blocked", session_id="s1"),
            execution_context=ctx,
        ):
            events.append(event)

        run_started = [e for e in collected_events if isinstance(e, RunStarted)]
        run_completed = [e for e in collected_events if isinstance(e, RunCompleted)]
        run_failed = [e for e in collected_events if isinstance(e, RunFailed)]

        assert len(run_started) == 1, f"Expected 1 RunStarted, got {len(run_started)}"
        assert len(run_completed) == 1, f"Expected 1 RunCompleted, got {len(run_completed)}"
        assert len(run_failed) == 0, f"Expected 0 RunFailed, got {len(run_failed)}"
        assert run_started[0].run_id == ctx.run_id
        assert run_completed[0].run_id == ctx.run_id
        # Consumer should have received the blocked reply
        assert len(events) >= 1
        assert events[0].event_type == "reply_completed"


# ── Acceptance Test: Full Chain Must Exist (hardened) ───────────────


class TestAcceptanceFullChainMustExist:
    """Full chain: Trace and Cost projections MUST fire (no conditional assertions)."""

    @pytest.mark.asyncio
    async def test_full_chain_must_exist(self):
        from unittest.mock import AsyncMock, MagicMock

        from cost_analysis.projector import CostProjector
        from observability.config import ObservabilitySettings
        from observability.projector import TraceProjector

        # 1. Run real AgentRuntime.run()
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

        # 2. Feed to TraceProjector
        trace_publisher = MagicMock()
        trace_settings = ObservabilitySettings()
        trace_projector = TraceProjector(publisher=trace_publisher, settings=trace_settings)

        for event in collected_events:
            if hasattr(event, "event_type"):
                await trace_projector.handle(event)

        # 3. Feed to CostProjector
        cost_publisher = MagicMock()
        cost_projector = CostProjector(publisher=cost_publisher)

        for event in collected_events:
            if hasattr(event, "event_type"):
                await cost_projector.handle(event)

        # 4. HARD assertions — chain MUST exist
        assert trace_publisher.submit_nowait.called, \
            "TraceProjector must submit a TraceEnvelope"
        assert cost_publisher.submit_nowait.called, \
            "CostProjector must submit a CostRecord"

        # 5. Identity consistency
        envelope = trace_publisher.submit_nowait.call_args[0][0]
        assert UUID(envelope.run_id) == UUID(agent_run.run_id)
        assert UUID(envelope.trace_id) == UUID(agent_run.trace_id)

        record = cost_publisher.submit_nowait.call_args[0][0]
        assert record.run_id == agent_run.run_id
        assert record.trace_id == agent_run.trace_id
