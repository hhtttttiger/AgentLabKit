"""Tests for Evaluation v2 contracts and adapters."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from evaluation.contracts import EvalCase, EvalMetricResult, EvalRunResult
from evaluation.contracts_v2 import (
    AgentRunSummary,
    DatasetExample,
    EvaluationContext,
    EvaluationResult,
    EvaluationRun,
    EvaluationRunStatus,
    MetricResult,
    SpanSummary,
    eval_case_to_dataset_example,
    eval_run_result_to_evaluation_result,
)


# ── DatasetExample ─────────────────────────────────────────────────


class TestDatasetExample:
    def test_basic_creation(self):
        example = DatasetExample(
            example_id="1",
            dataset_id="10",
            input_text="What is AI?",
            expected_output="AI is artificial intelligence.",
        )
        assert example.example_id == "1"
        assert example.dataset_id == "10"
        assert example.input_text == "What is AI?"
        assert example.expected_output == "AI is artificial intelligence."

    def test_optional_fields(self):
        example = DatasetExample(
            example_id="2",
            dataset_id="10",
            input_text="Hello",
        )
        assert example.expected_output is None
        assert example.context == []
        assert example.tags == []
        assert example.metadata == {}

    def test_with_context_and_tags(self):
        example = DatasetExample(
            example_id="3",
            dataset_id="10",
            input_text="What is ML?",
            context=["Machine learning is a subset of AI."],
            tags=["ml", "ai"],
            metadata={"difficulty": "easy"},
        )
        assert len(example.context) == 1
        assert len(example.tags) == 2
        assert example.metadata["difficulty"] == "easy"


# ── EvaluationContext ──────────────────────────────────────────────


class TestEvaluationContext:
    def test_basic_creation(self):
        example = DatasetExample(
            example_id="1",
            dataset_id="10",
            input_text="What is AI?",
        )
        context = EvaluationContext(example=example)
        assert context.example.example_id == "1"
        assert context.run is None
        assert context.spans == []

    def test_with_run_summary(self):
        example = DatasetExample(
            example_id="1",
            dataset_id="10",
            input_text="What is AI?",
        )
        run = AgentRunSummary(
            run_id="run-123",
            trace_id="trace-456",
            agent_key="chat",
            input_text="What is AI?",
            output_text="AI is artificial intelligence.",
            status="ok",
            duration_ms=1000,
            total_input_tokens=100,
            total_output_tokens=50,
            tool_call_count=0,
        )
        context = EvaluationContext(example=example, run=run)
        assert context.run.run_id == "run-123"
        assert context.run.agent_key == "chat"

    def test_with_spans(self):
        example = DatasetExample(
            example_id="1",
            dataset_id="10",
            input_text="What is AI?",
        )
        spans = [
            SpanSummary(
                span_id="span-1",
                name="llm.generate",
                kind="LLM_CALL",
                duration_ms=500,
                attributes={"model": "gpt-4o"},
            ),
        ]
        context = EvaluationContext(example=example, spans=spans)
        assert len(context.spans) == 1
        assert context.spans[0].name == "llm.generate"


# ── EvaluationResult ───────────────────────────────────────────────


class TestEvaluationResult:
    def test_basic_creation(self):
        result = EvaluationResult(example_id="1")
        assert result.example_id == "1"
        assert result.run_id is None
        assert result.metric_results == []
        assert result.overall_score == 0.0
        assert result.error_message is None

    def test_with_metrics(self):
        metrics = [
            MetricResult(metric_name="faithfulness", score=0.9, passed=True),
            MetricResult(metric_name="relevancy", score=0.8, passed=True),
        ]
        result = EvaluationResult(
            example_id="1",
            run_id="run-123",
            metric_results=metrics,
            overall_score=0.85,
        )
        assert len(result.metric_results) == 2
        assert result.overall_score == 0.85
        assert result.run_id == "run-123"

    def test_with_error(self):
        result = EvaluationResult(
            example_id="1",
            error_message="evaluation failed",
            duration_ms=100,
        )
        assert result.error_message == "evaluation failed"
        assert result.duration_ms == 100


# ── EvaluationRun ──────────────────────────────────────────────────


class TestEvaluationRun:
    def test_basic_creation(self):
        run = EvaluationRun(
            run_id="eval-run-1",
            dataset_id="dataset-1",
            agent_key="chat",
        )
        assert run.run_id == "eval-run-1"
        assert run.status == EvaluationRunStatus.PENDING
        assert run.total_examples == 0

    def test_status_enum(self):
        assert EvaluationRunStatus.PENDING == "pending"
        assert EvaluationRunStatus.RUNNING == "running"
        assert EvaluationRunStatus.COMPLETED == "completed"
        assert EvaluationRunStatus.FAILED == "failed"
        assert EvaluationRunStatus.CANCELLED == "cancelled"


# ── Adapters ───────────────────────────────────────────────────────


class TestAdapters:
    def test_eval_case_to_dataset_example(self):
        case = EvalCase(
            id=1,
            dataset_id=10,
            input_text="What is AI?",
            expected_output="AI is artificial intelligence.",
            context=["context1"],
            tags=["tag1"],
            metadata={"key": "value"},
        )
        example = eval_case_to_dataset_example(case)
        assert example.example_id == "1"
        assert example.dataset_id == "10"
        assert example.input_text == "What is AI?"
        assert example.expected_output == "AI is artificial intelligence."
        assert example.context == ["context1"]
        assert example.tags == ["tag1"]
        assert example.metadata == {"key": "value"}

    def test_eval_case_to_dataset_example_defaults(self):
        case = EvalCase(
            id=2,
            dataset_id=10,
            input_text="Hello",
        )
        example = eval_case_to_dataset_example(case)
        assert example.expected_output is None
        assert example.context == []
        assert example.tags == []
        assert example.metadata == {}

    def test_eval_run_result_to_evaluation_result(self):
        metric_results = [
            EvalMetricResult(metric_name="faithfulness", score=0.9, reasoning="good", passed=True),
        ]
        result = EvalRunResult(
            id=1,
            run_id=100,
            case_id=1,
            actual_output="AI is artificial intelligence.",
            metric_results=metric_results,
            overall_score=0.9,
            duration_ms=500,
        )
        eval_result = eval_run_result_to_evaluation_result(result)
        assert eval_result.example_id == "1"
        assert eval_result.run_id == "100"
        assert len(eval_result.metric_results) == 1
        assert eval_result.metric_results[0].metric_name == "faithfulness"
        assert eval_result.overall_score == 0.9
        assert eval_result.duration_ms == 500

    def test_eval_run_result_with_error(self):
        result = EvalRunResult(
            case_id=1,
            error_message="failed",
            duration_ms=100,
        )
        eval_result = eval_run_result_to_evaluation_result(result)
        assert eval_result.example_id == "1"
        assert eval_result.error_message == "failed"
        assert eval_result.run_id is None


# ── Evaluator Protocol ─────────────────────────────────────────────


class TestEvaluatorProtocol:
    def test_protocol_check(self):
        """验证 Evaluator 是一个 runtime_checkable Protocol。"""
        from evaluation.contracts_v2 import Evaluator

        # 一个实现了 Evaluator 协议的类
        class MockEvaluator:
            name = "mock"

            async def evaluate(self, context):
                return EvaluationResult(example_id=context.example.example_id)

            async def evaluate_batch(self, contexts):
                return [EvaluationResult(example_id=ctx.example.example_id) for ctx in contexts]

        evaluator = MockEvaluator()
        assert isinstance(evaluator, Evaluator)
