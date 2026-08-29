"""Tests for DatasetManager and DatasetEvaluationRunner."""

from __future__ import annotations

import pytest

from evaluation.contracts_v2 import (
    AgentRunSummary,
    DatasetExample,
    EvaluationContext,
    EvaluationResult,
    EvaluationRunStatus,
    MetricResult,
)
from evaluation.dataset import DatasetEvaluationRunner, DatasetManager, InMemoryDatasetStore


def _make_run(**kwargs) -> AgentRunSummary:
    defaults = {
        "run_id": "run-123",
        "trace_id": "trace-456",
        "agent_key": "chat",
        "input_text": "What is AI?",
        "output_text": "AI is artificial intelligence.",
        "status": "ok",
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

    async def evaluate(self, context):
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
        assert example.metadata["run_id"] == "run-123"

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

        assert result.status == EvaluationRunStatus.FAILED
        assert result.total_examples == 1
        assert result.completed_examples == 0
        assert result.failed_examples == 1
        assert result.results[0].error_message == "mock error"

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

        # 第一个成功，第二个失败
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

        assert result.status == EvaluationRunStatus.FAILED
        assert result.completed_examples == 1
        assert result.failed_examples == 1
        assert result.overall_score == 0.8  # 只计算成功的
