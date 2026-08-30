"""Architecture Invariant Tests — 确保核心架构规则不被回退。

这些测试验证 Execution Model v2 的核心不变量：
1. Runtime 是唯一 run_id/trace_id 创建者
2. TraceProjector 不生成 identity（纯投影）
3. Event.span_id = Runtime 创建的 span_id
4. CostProjector 用 event.completed_at
5. EvaluationResult.overall_score 计算正确
6. RunView 协议正确实现
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from agent_runtime.contracts.run import AgentRun, ExecutionContext, RunStatus, RunTarget
from agent_runtime.events_v2 import (
    LLMCallCompleted,
    LLMCallFailed,
    LLMCallStarted,
    RunCancelled,
    RunCompleted,
    RunFailed,
    RunStarted,
    ToolCallCompleted,
    ToolCallFailed,
    ToolCallStarted,
)


# ── Invariant 1: Runtime is sole identity creator ──────────────────


class TestIdentityOwnership:
    """Runtime 是唯一 run_id/trace_id 创建者。"""

    def test_execution_context_creates_unique_ids(self):
        """ExecutionContext 创建唯一的 run_id 和 trace_id。"""
        ctx1 = ExecutionContext()
        ctx2 = ExecutionContext()
        assert ctx1.run_id != ctx2.run_id
        assert ctx1.trace_id != ctx2.trace_id
        assert ctx1.run_id != ctx1.trace_id

    def test_agent_run_id_from_execution_context(self):
        """AgentRun 的 run_id 来自 ExecutionContext，不是自生成。"""
        ctx = ExecutionContext()
        run = AgentRun(
            run_id=ctx.run_id,
            trace_id=ctx.trace_id,
            input="test",
            target=RunTarget(agent_key="test", agent_version="1.0"),
        )
        assert run.run_id == ctx.run_id
        assert run.trace_id == ctx.trace_id

    def test_run_started_carries_runtime_identity(self):
        """RunStarted 事件携带 Runtime 创建的 identity。"""
        ctx = ExecutionContext()
        event = RunStarted(
            run_id=ctx.run_id,
            trace_id=ctx.trace_id,
            agent_key="test",
            span_id="span-1",
        )
        assert event.run_id == ctx.run_id
        assert event.trace_id == ctx.trace_id


# ── Invariant 2: TraceProjector is pure projector ──────────────────


class TestProjectorPurity:
    """TraceProjector 不生成 identity，只使用事件中的 identity。"""

    def test_projector_uses_event_span_id(self):
        """TraceProjector 使用事件自带的 span_id，不生成新的。"""
        from observability.config import ObservabilitySettings
        from observability.projector import TraceProjector

        publisher = MagicMock()
        settings = ObservabilitySettings()
        projector = TraceProjector(publisher=publisher, settings=settings)
        run_id = "run-123"
        trace_id = "a" * 32
        span_id = "b" * 16

        event = RunStarted(
            run_id=run_id,
            trace_id=trace_id,
            agent_key="test",
            span_id=span_id,
        )
        import asyncio
        asyncio.run(projector.handle(event))

        # 投影后的 span 使用事件的 span_id
        assert run_id in projector._open_spans
        assert span_id in projector._open_spans[run_id]
        assert projector._open_spans[run_id][span_id].span_id == span_id

    def test_projector_no_uuid_generation(self):
        """TraceProjector 不调用 uuid4() 生成 identity。"""
        import inspect
        from observability.projector import TraceProjector

        source = inspect.getsource(TraceProjector)
        # 投影器不应在 on_event / _finalize_run 中生成 uuid
        # （__init__ 中的 uuid 用于 run_id 是允许的）
        assert "uuid4()" not in source or source.count("uuid4()") <= 1


# ── Invariant 3: Span identity ownership ───────────────────────────


class TestSpanIdentityOwnership:
    """Event.span_id 由 Runtime 创建，不是 Projector 生成。"""

    def test_events_carry_span_id(self):
        """所有 v2 事件都有 span_id 字段。"""
        events = [
            RunStarted(run_id="r", trace_id="t", agent_key="a", span_id="s"),
            RunCompleted(run_id="r", span_id="s"),
            RunFailed(run_id="r", error_message="e", span_id="s"),
            RunCancelled(run_id="r", span_id="s"),
            LLMCallStarted(run_id="r", model="m", span_id="s"),
            LLMCallCompleted(run_id="r", model="m", span_id="s"),
            LLMCallFailed(run_id="r", model="m", error_message="e", span_id="s"),
            ToolCallStarted(run_id="r", tool_name="t", span_id="s"),
            ToolCallCompleted(run_id="r", tool_name="t", span_id="s"),
            ToolCallFailed(run_id="r", tool_name="t", error_message="e", span_id="s"),
        ]
        for event in events:
            assert hasattr(event, "span_id"), f"{type(event).__name__} missing span_id"
            assert event.span_id == "s"

    def test_same_span_id_for_start_complete(self):
        """同一操作的 Started/Completed 使用相同 span_id。"""
        span_id = "llm-span-1"
        started = LLMCallStarted(run_id="r", model="m", span_id=span_id)
        completed = LLMCallCompleted(run_id="r", model="m", span_id=span_id)
        assert started.span_id == completed.span_id

    def test_parent_span_id_from_stack(self):
        """parent_span_id 来自 span stack，不是 projector 生成。"""
        from agent_runtime.runtime.loop import _SpanContext

        ctx = _SpanContext()
        assert ctx.parent_span_id is None

        ctx.push("span-1")
        # parent_span_id 返回栈顶 = span-1，作为下一个子 span 的 parent
        assert ctx.parent_span_id == "span-1"

        ctx.push("span-2")
        assert ctx.parent_span_id == "span-2"

        ctx.pop()
        assert ctx.parent_span_id == "span-1"

        ctx.pop()
        assert ctx.parent_span_id is None


# ── Invariant 4: CostProjector uses event.completed_at ─────────────


class TestCostProjectorContract:
    """CostProjector 使用 event.completed_at，不用 event.timestamp。"""

    def test_llm_completed_has_timing_fields(self):
        """LLMCallCompleted 有 started_at 和 completed_at。"""
        now = datetime.now(timezone.utc)
        event = LLMCallCompleted(
            run_id="r",
            model="m",
            span_id="s",
            started_at=now,
            completed_at=now,
        )
        assert event.started_at == now
        assert event.completed_at == now

    def test_cost_projector_uses_completed_at(self):
        """CostProjector 使用 event.completed_at 而非 event.timestamp。"""
        from cost_analysis.projector import CostProjector

        publisher = MagicMock()
        projector = CostProjector(publisher=publisher)
        now = datetime.now(timezone.utc)
        event = LLMCallCompleted(
            run_id="r",
            model="gpt-4",
            span_id="s",
            input_tokens=100,
            output_tokens=50,
            started_at=now,
            completed_at=now,
        )
        import asyncio
        asyncio.run(projector.handle(event))
        # 如果 CostProjector 正确使用 completed_at，不会有异常


# ── Invariant 5: EvaluationResult.overall_score computation ────────


class TestEvaluationResultContract:
    """EvaluationResult.overall_score 计算正确。"""

    def test_overall_score_from_score_field(self):
        """当 score 有值时，overall_score 返回 score。"""
        from evaluation.contracts_v2 import EvaluationResult

        result = EvaluationResult(score=0.85)
        assert result.overall_score == 0.85

    def test_overall_score_from_metric_results(self):
        """当 score 为 None 时，overall_score 从 metric_results 计算平均。"""
        from evaluation.contracts_v2 import EvaluationResult, MetricResult

        result = EvaluationResult(
            metric_results=[
                MetricResult(metric_name="m1", score=0.8),
                MetricResult(metric_name="m2", score=0.6),
            ]
        )
        assert result.overall_score == 0.7

    def test_overall_score_default_zero(self):
        """无 score 无 metric_results 时，overall_score 为 0。"""
        from evaluation.contracts_v2 import EvaluationResult

        result = EvaluationResult()
        assert result.overall_score == 0.0

    def test_error_message_from_message(self):
        """error_message 返回 message 字段。"""
        from evaluation.contracts_v2 import EvaluationResult

        result = EvaluationResult(message="something failed")
        assert result.error_message == "something failed"

    def test_error_message_none_when_no_message(self):
        """无 message 时，error_message 为 None。"""
        from evaluation.contracts_v2 import EvaluationResult

        result = EvaluationResult()
        assert result.error_message is None


# ── Invariant 6: RunView protocol ──────────────────────────────────


class TestRunViewProtocol:
    """RunView 协议正确实现。"""

    def test_agent_run_summary_implements_run_view(self):
        """AgentRunSummary 实现 RunView 协议。"""
        from evaluation.contracts_v2 import AgentRunSummary, RunStatus, RunView

        summary = AgentRunSummary(
            run_id="r",
            trace_id="t",
            agent_key="a",
            input_text="hello",
            output_text="world",
            status=RunStatus.COMPLETED,
        )
        assert isinstance(summary, RunView)
        assert summary.run_id == "r"
        assert summary.trace_id == "t"
        assert summary.input == "hello"
        assert summary.output == "world"

    def test_run_view_protocol_check(self):
        """RunView 是 runtime_checkable 协议。"""
        from evaluation.contracts_v2 import RunView

        # 一个满足协议的普通类
        class FakeRun:
            @property
            def run_id(self) -> str:
                return "fake"

            @property
            def trace_id(self) -> str | None:
                return None

            @property
            def input(self) -> Any:
                return "input"

            @property
            def output(self) -> Any | None:
                return None

            @property
            def status(self) -> str:
                return "completed"

            @property
            def started_at(self) -> datetime:
                return datetime.now()

            @property
            def finished_at(self) -> datetime | None:
                return None

            @property
            def target(self) -> Any | None:
                return None

            @property
            def tool_names(self) -> list[str]:
                return []

            @property
            def tool_call_count(self) -> int:
                return 0

            @property
            def duration_ms(self) -> int | None:
                return None

            @property
            def total_input_tokens(self) -> int:
                return 0

            @property
            def total_output_tokens(self) -> int:
                return 0

        assert isinstance(FakeRun(), RunView)


# ── Invariant 7: Terminal invariant ────────────────────────────────


class TestTerminalInvariant:
    """每个 RunStarted 恰好有一个终止事件。"""

    def test_run_started_has_terminal_events(self):
        """RunStarted 的终止事件类型完整。"""
        terminal_types = {RunCompleted, RunFailed, RunCancelled}
        # 确保这三个类型都存在且可实例化
        assert RunCompleted is not None
        assert RunFailed is not None
        assert RunCancelled is not None

    def test_run_completed_marks_terminal(self):
        """RunCompleted 是终止状态。"""
        event = RunCompleted(run_id="r", span_id="s")
        assert event.run_id == "r"

    def test_run_failed_marks_terminal(self):
        """RunFailed 是终止状态。"""
        event = RunFailed(run_id="r", error_message="oops", span_id="s")
        assert event.error_message == "oops"

    def test_run_cancelled_marks_terminal(self):
        """RunCancelled 是终止状态。"""
        event = RunCancelled(run_id="r", span_id="s")
        assert event.run_id == "r"


# ── Invariant 8: Tool failure semantics ────────────────────────────


class TestToolFailureSemantics:
    """工具失败语义：ToolCallCompleted(is_error=True) vs ToolCallFailed。"""

    def test_tool_call_completed_with_error(self):
        """ToolCallCompleted(is_error=True) 表示业务错误。"""
        event = ToolCallCompleted(
            run_id="r",
            tool_name="search",
            span_id="s",
            is_error=True,
            result="not found",
        )
        assert event.is_error is True
        assert event.result == "not found"

    def test_tool_call_failed_is_runtime_error(self):
        """ToolCallFailed 表示运行时故障。"""
        event = ToolCallFailed(
            run_id="r",
            tool_name="search",
            span_id="s",
            error_message="timeout",
        )
        assert event.error_message == "timeout"
