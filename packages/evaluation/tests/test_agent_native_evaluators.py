"""Tests for Agent Native Evaluators."""

from __future__ import annotations

import pytest

from evaluation.contracts_v2 import (
    AgentRunSummary,
    DatasetExample,
    EvaluationContext,
    RunStatus,
    SpanSummary,
)
from evaluation.evaluators.agent_native import (
    CostEvaluator,
    LatencyEvaluator,
    MaxStepsEvaluator,
    NoErrorEvaluator,
    ToolArgsEvaluator,
    ToolCalledEvaluator,
    ToolNotCalledEvaluator,
    TrajectoryEvaluator,
)


def _make_example(example_id: str = "1") -> DatasetExample:
    return DatasetExample(
        example_id=example_id,
        dataset_id="10",
        input_text="What is AI?",
    )


def _make_run(**kwargs) -> AgentRunSummary:
    defaults = {
        "run_id": "run-123",
        "trace_id": "trace-456",
        "agent_key": "chat",
        "input_text": "What is AI?",
        "output_text": "AI is artificial intelligence.",
        "status": RunStatus.COMPLETED,
        "duration_ms": 1000,
        "total_input_tokens": 100,
        "total_output_tokens": 50,
        "tool_call_count": 1,
        "tool_names": ["search"],
    }
    defaults.update(kwargs)
    return AgentRunSummary(**defaults)


def _make_span(name: str, **kwargs) -> SpanSummary:
    return SpanSummary(
        span_id="span-1",
        name=name,
        kind="internal",
        duration_ms=100,
        attributes=dict(kwargs),
    )


# ── ToolCalledEvaluator ────────────────────────────────────────────


class TestToolCalledEvaluator:
    @pytest.mark.asyncio
    async def test_tool_called_from_run(self):
        evaluator = ToolCalledEvaluator(tool_name="search")
        context = EvaluationContext(
            example=_make_example(),
            run=_make_run(tool_names=["search", "calculate"]),
        )
        result = await evaluator.evaluate(context)
        assert result.overall_score == 1.0
        assert result.metric_results[0].passed is True

    @pytest.mark.asyncio
    async def test_tool_not_called_from_run(self):
        evaluator = ToolCalledEvaluator(tool_name="search")
        context = EvaluationContext(
            example=_make_example(),
            run=_make_run(tool_names=["calculate"]),
        )
        result = await evaluator.evaluate(context)
        assert result.overall_score == 0.0
        assert result.metric_results[0].passed is False

    @pytest.mark.asyncio
    async def test_tool_called_from_spans(self):
        evaluator = ToolCalledEvaluator(tool_name="search")
        span = SpanSummary(
            span_id="span-1",
            name="tool.search",
            kind="internal",
            duration_ms=100,
            attributes={"tool.name": "search"},
        )
        context = EvaluationContext(
            example=_make_example(),
            spans=[span],
        )
        result = await evaluator.evaluate(context)
        assert result.overall_score == 1.0

    @pytest.mark.asyncio
    async def test_no_run_no_spans(self):
        evaluator = ToolCalledEvaluator(tool_name="search")
        context = EvaluationContext(example=_make_example())
        result = await evaluator.evaluate(context)
        assert result.overall_score == 0.0


# ── ToolNotCalledEvaluator ─────────────────────────────────────────


class TestToolNotCalledEvaluator:
    @pytest.mark.asyncio
    async def test_tool_not_called(self):
        evaluator = ToolNotCalledEvaluator(tool_name="search")
        context = EvaluationContext(
            example=_make_example(),
            run=_make_run(tool_names=["calculate"]),
        )
        result = await evaluator.evaluate(context)
        assert result.overall_score == 1.0
        assert result.metric_results[0].passed is True

    @pytest.mark.asyncio
    async def test_tool_was_called(self):
        evaluator = ToolNotCalledEvaluator(tool_name="search")
        context = EvaluationContext(
            example=_make_example(),
            run=_make_run(tool_names=["search"]),
        )
        result = await evaluator.evaluate(context)
        assert result.overall_score == 0.0
        assert result.metric_results[0].passed is False


# ── MaxStepsEvaluator ──────────────────────────────────────────────


class TestMaxStepsEvaluator:
    @pytest.mark.asyncio
    async def test_within_limit(self):
        evaluator = MaxStepsEvaluator(max_steps=5)
        context = EvaluationContext(
            example=_make_example(),
            run=_make_run(tool_call_count=3),
        )
        result = await evaluator.evaluate(context)
        assert result.overall_score == 1.0
        assert result.metric_results[0].passed is True

    @pytest.mark.asyncio
    async def test_exceeds_limit(self):
        evaluator = MaxStepsEvaluator(max_steps=5)
        context = EvaluationContext(
            example=_make_example(),
            run=_make_run(tool_call_count=10),
        )
        result = await evaluator.evaluate(context)
        assert result.overall_score == 0.0
        assert result.metric_results[0].passed is False

    @pytest.mark.asyncio
    async def test_exact_limit(self):
        evaluator = MaxStepsEvaluator(max_steps=5)
        context = EvaluationContext(
            example=_make_example(),
            run=_make_run(tool_call_count=5),
        )
        result = await evaluator.evaluate(context)
        assert result.overall_score == 1.0

    @pytest.mark.asyncio
    async def test_fallback_to_span_count(self):
        evaluator = MaxStepsEvaluator(max_steps=5)
        context = EvaluationContext(
            example=_make_example(),
            spans=[_make_span("tool.search"), _make_span("tool.calculate")],
        )
        result = await evaluator.evaluate(context)
        assert result.overall_score == 1.0


# ── LatencyEvaluator ───────────────────────────────────────────────


class TestLatencyEvaluator:
    @pytest.mark.asyncio
    async def test_within_limit(self):
        evaluator = LatencyEvaluator(max_duration_ms=5000)
        context = EvaluationContext(
            example=_make_example(),
            run=_make_run(duration_ms=1000),
        )
        result = await evaluator.evaluate(context)
        assert result.overall_score == 1.0

    @pytest.mark.asyncio
    async def test_exceeds_limit(self):
        evaluator = LatencyEvaluator(max_duration_ms=1000)
        context = EvaluationContext(
            example=_make_example(),
            run=_make_run(duration_ms=5000),
        )
        result = await evaluator.evaluate(context)
        assert result.overall_score == 0.0


# ── CostEvaluator ──────────────────────────────────────────────────


class TestCostEvaluator:
    @pytest.mark.asyncio
    async def test_within_budget(self):
        evaluator = CostEvaluator(max_cost_usd=1.0)
        context = EvaluationContext(
            example=_make_example(),
            run=_make_run(total_input_tokens=100, total_output_tokens=50),
        )
        result = await evaluator.evaluate(context)
        # 150 tokens * $0.01/1K = $0.0015, within $1.0
        assert result.overall_score == 1.0

    @pytest.mark.asyncio
    async def test_exceeds_budget(self):
        evaluator = CostEvaluator(max_cost_usd=0.001)
        context = EvaluationContext(
            example=_make_example(),
            run=_make_run(total_input_tokens=1000, total_output_tokens=500),
        )
        result = await evaluator.evaluate(context)
        # 1500 tokens * $0.01/1K = $0.015, exceeds $0.001
        assert result.overall_score == 0.0


# ── NoErrorEvaluator ───────────────────────────────────────────────


class TestNoErrorEvaluator:
    @pytest.mark.asyncio
    async def test_no_error(self):
        evaluator = NoErrorEvaluator()
        context = EvaluationContext(
            example=_make_example(),
            run=_make_run(status=RunStatus.COMPLETED),
        )
        result = await evaluator.evaluate(context)
        assert result.overall_score == 1.0
        assert result.metric_results[0].passed is True

    @pytest.mark.asyncio
    async def test_with_error_status(self):
        evaluator = NoErrorEvaluator()
        context = EvaluationContext(
            example=_make_example(),
            run=_make_run(status=RunStatus.FAILED),
        )
        result = await evaluator.evaluate(context)
        assert result.overall_score == 0.0
        assert result.metric_results[0].passed is False

    @pytest.mark.asyncio
    async def test_with_error_span(self):
        evaluator = NoErrorEvaluator()
        context = EvaluationContext(
            example=_make_example(),
            spans=[_make_span("llm.generate", status="error")],
        )
        result = await evaluator.evaluate(context)
        assert result.overall_score == 0.0

    @pytest.mark.asyncio
    async def test_cancelled_status(self):
        evaluator = NoErrorEvaluator()
        context = EvaluationContext(
            example=_make_example(),
            run=_make_run(status="cancelled"),
        )
        result = await evaluator.evaluate(context)
        assert result.overall_score == 0.0


# ── TrajectoryEvaluator ────────────────────────────────────────────


class TestTrajectoryEvaluator:
    @pytest.mark.asyncio
    async def test_matching_trajectory(self):
        evaluator = TrajectoryEvaluator(
            expected_trajectory=["agent.run", "agent.process", "llm.generate"],
        )
        context = EvaluationContext(
            example=_make_example(),
            spans=[
                _make_span("agent.run"),
                _make_span("agent.process"),
                _make_span("llm.generate"),
            ],
        )
        result = await evaluator.evaluate(context)
        assert result.overall_score == 1.0
        assert result.metric_results[0].passed is True

    @pytest.mark.asyncio
    async def test_mismatched_trajectory(self):
        evaluator = TrajectoryEvaluator(
            expected_trajectory=["agent.run", "llm.generate", "agent.process"],
        )
        context = EvaluationContext(
            example=_make_example(),
            spans=[
                _make_span("agent.run"),
                _make_span("agent.process"),
                _make_span("llm.generate"),
            ],
        )
        result = await evaluator.evaluate(context)
        assert result.overall_score == 0.0
        assert result.metric_results[0].passed is False

    @pytest.mark.asyncio
    async def test_wildcard_trajectory(self):
        evaluator = TrajectoryEvaluator(
            expected_trajectory=["agent.run", "*", "llm.generate"],
        )
        context = EvaluationContext(
            example=_make_example(),
            spans=[
                _make_span("agent.run"),
                _make_span("agent.process"),
                _make_span("llm.generate"),
            ],
        )
        result = await evaluator.evaluate(context)
        assert result.overall_score == 1.0

    @pytest.mark.asyncio
    async def test_too_few_spans(self):
        evaluator = TrajectoryEvaluator(
            expected_trajectory=["agent.run", "agent.process", "llm.generate"],
        )
        context = EvaluationContext(
            example=_make_example(),
            spans=[_make_span("agent.run")],
        )
        result = await evaluator.evaluate(context)
        assert result.overall_score == 0.0

    @pytest.mark.asyncio
    async def test_prefix_matching(self):
        """轨迹匹配是前缀匹配，多余的 span 不影响结果。"""
        evaluator = TrajectoryEvaluator(
            expected_trajectory=["agent.run", "agent.process"],
        )
        context = EvaluationContext(
            example=_make_example(),
            spans=[
                _make_span("agent.run"),
                _make_span("agent.process"),
                _make_span("llm.generate"),
                _make_span("tool.search"),
            ],
        )
        result = await evaluator.evaluate(context)
        assert result.overall_score == 1.0


# ── Batch Evaluation ───────────────────────────────────────────────


class TestBatchEvaluation:
    @pytest.mark.asyncio
    async def test_batch_evaluate(self):
        evaluator = ToolCalledEvaluator(tool_name="search")
        contexts = [
            EvaluationContext(
                example=_make_example("1"),
                run=_make_run(tool_names=["search"]),
            ),
            EvaluationContext(
                example=_make_example("2"),
                run=_make_run(tool_names=["calculate"]),
            ),
        ]
        results = await evaluator.evaluate_batch(contexts)
        assert len(results) == 2
        assert results[0].overall_score == 1.0
        assert results[1].overall_score == 0.0

    @pytest.mark.asyncio
    async def test_empty_batch(self):
        evaluator = ToolCalledEvaluator(tool_name="search")
        results = await evaluator.evaluate_batch([])
        assert results == []
