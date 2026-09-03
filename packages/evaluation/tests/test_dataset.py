"""Tests for DatasetManager and DatasetEvaluationRunner — v2 with RunExecutor."""

from __future__ import annotations

import pytest

from evaluation.contracts_v2 import (
    AgentRunSummary,
    DatasetExample,
    EvaluationContext,
    EvaluationResult,
    EvaluationRunStatus,
    Expectation,
    ExpectationType,
    MetricResult,
    RunStatus,
    RunView,
)
from evaluation.dataset import (
    DatasetEvaluationRunner,
    DatasetManager,
    InMemoryDatasetStore,
    run_to_example,
)
from evaluation.replay import MockRunExecutor, RunTarget


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


class MockEvaluator:
    """模拟评估器，返回预设结果。"""

    def __init__(self, score: float = 1.0, error: bool = False) -> None:
        self.name = "mock"
        self.score = score
        self.error = error
        self.last_context: EvaluationContext | None = None

    async def evaluate(self, context):
        self.last_context = context
        if self.error:
            return EvaluationResult(
                example_id=context.example.example_id,
                message="mock error",
            )
        return EvaluationResult(
            example_id=context.example.example_id,
            score=self.score,
            metric_results=[MetricResult(metric_name="mock", score=self.score, passed=self.score > 0.5)],
        )

    async def evaluate_batch(self, contexts):
        return [await self.evaluate(ctx) for ctx in contexts]


# ── InMemoryDatasetStore ───────────────────────────────────────────


class TestInMemoryDatasetStore:
    @pytest.mark.asyncio
    async def test_create_dataset(self):
        store = InMemoryDatasetStore()
        dataset_id = await store.create_dataset("test dataset", "a test")
        assert dataset_id
        assert dataset_id in store._datasets

    @pytest.mark.asyncio
    async def test_add_and_get_examples(self):
        store = InMemoryDatasetStore()
        dataset_id = await store.create_dataset("test")

        example = DatasetExample(
            example_id="1",
            dataset_id=dataset_id,
            input_text="Hello",
        )
        await store.add_example(example)

        examples = await store.get_examples(dataset_id)
        assert len(examples) == 1
        assert examples[0].example_id == "1"

    @pytest.mark.asyncio
    async def test_delete_example(self):
        store = InMemoryDatasetStore()
        example = DatasetExample(
            example_id="1",
            dataset_id="10",
            input_text="Hello",
        )
        await store.add_example(example)
        await store.delete_example("1")

        examples = await store.get_examples("10")
        assert len(examples) == 0

    @pytest.mark.asyncio
    async def test_get_examples_different_datasets(self):
        store = InMemoryDatasetStore()
        await store.add_example(DatasetExample(example_id="1", dataset_id="10", input_text="A"))
        await store.add_example(DatasetExample(example_id="2", dataset_id="20", input_text="B"))

        examples_10 = await store.get_examples("10")
        examples_20 = await store.get_examples("20")
        assert len(examples_10) == 1
        assert len(examples_20) == 1


# ── DatasetManager ─────────────────────────────────────────────────


class TestDatasetManager:
    @pytest.mark.asyncio
    async def test_create_dataset(self):
        store = InMemoryDatasetStore()
        manager = DatasetManager(store)
        dataset_id = await manager.create_dataset("test")
        assert dataset_id

    @pytest.mark.asyncio
    async def test_add_example(self):
        store = InMemoryDatasetStore()
        manager = DatasetManager(store)
        dataset_id = await manager.create_dataset("test")

        example = DatasetExample(
            example_id="1",
            dataset_id=dataset_id,
            input_text="Hello",
        )
        await manager.add_example(example)

        examples = await manager.get_examples(dataset_id)
        assert len(examples) == 1

    @pytest.mark.asyncio
    async def test_add_examples_batch(self):
        store = InMemoryDatasetStore()
        manager = DatasetManager(store)
        dataset_id = await manager.create_dataset("test")

        examples = [
            DatasetExample(example_id="1", dataset_id=dataset_id, input_text="A"),
            DatasetExample(example_id="2", dataset_id=dataset_id, input_text="B"),
        ]
        await manager.add_examples(examples)

        result = await manager.get_examples(dataset_id)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_run_to_example(self):
        store = InMemoryDatasetStore()
        manager = DatasetManager(store)
        dataset_id = await manager.create_dataset("test")

        run = _make_run()
        example = await manager.run_to_example(run, dataset_id)

        assert example.dataset_id == dataset_id
        assert example.input_text == "What is AI?"
        assert example.expected_output == "AI is artificial intelligence."
        assert "from_run" in example.tags
        assert example.source_run_id == "run-123"

    @pytest.mark.asyncio
    async def test_run_to_example_with_custom_tags(self):
        store = InMemoryDatasetStore()
        manager = DatasetManager(store)
        dataset_id = await manager.create_dataset("test")

        run = _make_run()
        example = await manager.run_to_example(
            run, dataset_id,
            tags=["regression", "failed"],
            metadata={"issue": "BUG-123"},
        )

        assert "regression" in example.tags
        assert "failed" in example.tags
        assert example.metadata["issue"] == "BUG-123"

    @pytest.mark.asyncio
    async def test_run_to_example_with_context(self):
        from evaluation.contracts_v2 import SpanSummary

        store = InMemoryDatasetStore()
        manager = DatasetManager(store)
        dataset_id = await manager.create_dataset("test")

        run = _make_run()
        spans = [
            SpanSummary(
                span_id="span-1",
                name="tool.search",
                kind="internal",
                duration_ms=100,
                attributes={"tool.name": "search"},
            ),
        ]
        example = await manager.run_to_example_with_context(run, spans, dataset_id)

        assert len(example.context) == 1
        assert "Tool used: search" in example.context

    @pytest.mark.asyncio
    async def test_add_run_with_expectations(self):
        """add_run 支持 expectations 参数。"""
        store = InMemoryDatasetStore()
        manager = DatasetManager(store)
        dataset_id = await manager.create_dataset("test")

        run = _make_run()
        expectations = [
            Expectation(type=ExpectationType.TOOL_CALLED, value="search"),
        ]
        example = await manager.add_run(
            run, dataset_id,
            expectations=expectations,
        )

        assert len(example.expectations) == 1
        assert example.expectations[0].type == ExpectationType.TOOL_CALLED
        assert example.source_run_id == "run-123"


# ── run_to_example (pure function) ─────────────────────────────────


class TestRunToExample:
    def test_basic_conversion(self):
        run = _make_run()
        example = run_to_example(run, "dataset-1")

        assert example.dataset_id == "dataset-1"
        assert example.input_text == "What is AI?"
        assert example.source_run_id == "run-123"

    def test_with_expectations(self):
        run = _make_run()
        expectations = [
            Expectation(type=ExpectationType.TOOL_CALLED, value="search"),
            Expectation(type=ExpectationType.MAX_STEPS, value=5),
        ]
        example = run_to_example(run, "d1", expectations=expectations)

        assert len(example.expectations) == 2

    def test_with_custom_expected_output(self):
        run = _make_run()
        example = run_to_example(run, "d1", expected_output="custom expected")

        assert example.expected_output == "custom expected"


# ── DatasetEvaluationRunner ────────────────────────────────────────


class TestDatasetEvaluationRunner:
    @pytest.mark.asyncio
    async def test_run_evaluation(self):
        store = InMemoryDatasetStore()
        dataset_id = await store.create_dataset("test")
        await store.add_example(DatasetExample(
            example_id="1", dataset_id=dataset_id, input_text="A",
        ))
        await store.add_example(DatasetExample(
            example_id="2", dataset_id=dataset_id, input_text="B",
        ))

        evaluator = MockEvaluator(score=0.9)
        runner = DatasetEvaluationRunner(evaluator, store)

        result = await runner.run(dataset_id, "chat")

        assert result.status == EvaluationRunStatus.COMPLETED
        assert result.total_examples == 2
        assert result.completed_examples == 2
        assert result.failed_examples == 0
        assert result.overall_score == 0.9
        assert len(result.results) == 2

    @pytest.mark.asyncio
    async def test_run_evaluation_with_errors(self):
        store = InMemoryDatasetStore()
        dataset_id = await store.create_dataset("test")
        await store.add_example(DatasetExample(
            example_id="1", dataset_id=dataset_id, input_text="A",
        ))

        evaluator = MockEvaluator(error=True)
        runner = DatasetEvaluationRunner(evaluator, store)

        result = await runner.run(dataset_id, "chat")

        # A returned result with a message is still a completed evaluator
        # outcome (for example SKIPPED); only exceptions fail orchestration.
        assert result.status == EvaluationRunStatus.COMPLETED
        assert result.total_examples == 1
        assert result.completed_examples == 1
        assert result.failed_examples == 0
        assert result.results[0].error_message == "mock error"

    @pytest.mark.asyncio
    async def test_evaluator_exception_fails_orchestration(self):
        store = InMemoryDatasetStore()
        dataset_id = await store.create_dataset("test")
        await store.add_example(DatasetExample(
            example_id="1", dataset_id=dataset_id, input_text="A",
        ))

        class BrokenEvaluator:
            name = "broken"

            async def evaluate(self, context):
                raise RuntimeError("boom")

        result = await DatasetEvaluationRunner(BrokenEvaluator(), store).run(
            dataset_id, "chat"
        )

        assert result.status == EvaluationRunStatus.FAILED
        assert result.completed_examples == 0
        assert result.failed_examples == 1
        assert "boom" in result.results[0].error_message

    @pytest.mark.asyncio
    async def test_run_empty_dataset(self):
        store = InMemoryDatasetStore()
        dataset_id = await store.create_dataset("test")

        evaluator = MockEvaluator()
        runner = DatasetEvaluationRunner(evaluator, store)

        result = await runner.run(dataset_id, "chat")

        assert result.status == EvaluationRunStatus.FAILED
        assert result.error_message == "dataset is empty"

    @pytest.mark.asyncio
    async def test_run_mixed_results(self):
        store = InMemoryDatasetStore()
        dataset_id = await store.create_dataset("test")
        await store.add_example(DatasetExample(
            example_id="1", dataset_id=dataset_id, input_text="A",
        ))
        await store.add_example(DatasetExample(
            example_id="2", dataset_id=dataset_id, input_text="B",
        ))

        # 第一个成功，第二个返回一个非通过结果
        class MixedEvaluator:
            name = "mixed"
            _call_count = 0

            async def evaluate(self, context):
                MixedEvaluator._call_count += 1
                if MixedEvaluator._call_count == 1:
                    return EvaluationResult(
                        example_id=context.example.example_id,
                        score=0.8,
                    )
                return EvaluationResult(
                    example_id=context.example.example_id,
                    message="failed",
                )

            async def evaluate_batch(self, contexts):
                return [await self.evaluate(ctx) for ctx in contexts]

        runner = DatasetEvaluationRunner(MixedEvaluator(), store)
        result = await runner.run(dataset_id, "chat")

        assert result.status == EvaluationRunStatus.COMPLETED
        assert result.completed_examples == 2
        assert result.failed_examples == 0
        assert result.overall_score == 0.8  # 无 score 的结果不参与平均

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_runtime_execution_failure_fails_run_without_evaluation_verdict(self):
        store = InMemoryDatasetStore()
        dataset_id = await store.create_dataset("test")
        await store.add_example(DatasetExample(
            example_id="1", dataset_id=dataset_id, input_text="A",
        ))

        class FailingExecutor:
            async def execute(self, **kwargs):
                raise RuntimeError("runtime failed")

        result = await DatasetEvaluationRunner(
            MockEvaluator(), store, run_executor=FailingExecutor(), target=RunTarget(agent_key="chat")
        ).run(dataset_id, "chat")

        assert result.status == EvaluationRunStatus.FAILED
        assert result.failed_examples == 1
        assert result.results[0].passed is None
        assert "runtime failed" in result.results[0].error_message

    @pytest.mark.asyncio
    async def test_run_with_executor_populates_context_run(self):
        """RunExecutor 真实执行，EvaluationContext.run 包含真实 RunView。"""
        store = InMemoryDatasetStore()
        dataset_id = await store.create_dataset("test")
        await store.add_example(DatasetExample(
            example_id="1", dataset_id=dataset_id, input_text="What is AI?",
        ))

        evaluator = MockEvaluator(score=0.9)
        executor = MockRunExecutor(
            output_text="AI is artificial intelligence.",
            run_id="exec-run-1",
            trace_id="exec-trace-1",
        )
        target = RunTarget(agent_key="test-agent")
        runner = DatasetEvaluationRunner(evaluator, store, run_executor=executor, target=target)

        result = await runner.run(dataset_id, "test-agent")

        assert result.status == EvaluationRunStatus.COMPLETED
        # Evaluator 收到了包含真实 Run 的 context
        assert evaluator.last_context is not None
        assert evaluator.last_context.run is not None
        assert evaluator.last_context.run.run_id == "exec-run-1"

    @pytest.mark.asyncio
    async def test_run_without_executor_context_run_is_none(self):
        """没有 RunExecutor 时，EvaluationContext.run 为 None。"""
        store = InMemoryDatasetStore()
        dataset_id = await store.create_dataset("test")
        await store.add_example(DatasetExample(
            example_id="1", dataset_id=dataset_id, input_text="A",
        ))

        evaluator = MockEvaluator(score=0.9)
        runner = DatasetEvaluationRunner(evaluator, store)

        result = await runner.run(dataset_id, "chat")

        assert result.status == EvaluationRunStatus.COMPLETED
        assert evaluator.last_context is not None
        assert evaluator.last_context.run is None
