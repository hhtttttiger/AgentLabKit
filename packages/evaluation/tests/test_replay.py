"""Tests for Replay MVP."""

from __future__ import annotations

import pytest

from evaluation.contracts_v2 import (
    AgentRunSummary,
    DatasetExample,
    EvaluationContext,
    EvaluationResult,
    MetricResult,
)
from evaluation.replay import (
    InMemoryRunStore,
    MockRunExecutor,
    ReplayConfig,
    ReplayRunner,
)


def _make_run(run_id: str = "run-123", **kwargs) -> AgentRunSummary:
    defaults = {
        "run_id": run_id,
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
    """模拟评估器。"""

    def __init__(self, score: float = 0.8) -> None:
        self.name = "mock"
        self.score = score

    async def evaluate(self, context):
        return EvaluationResult(
            example_id=context.example.example_id,
            overall_score=self.score,
            metric_results=[MetricResult(metric_name="mock", score=self.score)],
        )

    async def evaluate_batch(self, contexts):
        return [await self.evaluate(ctx) for ctx in contexts]


# ── InMemoryRunStore ───────────────────────────────────────────────


class TestInMemoryRunStore:
    @pytest.mark.asyncio
    async def test_save_and_get(self):
        store = InMemoryRunStore()
        run = _make_run()
        await store.save_run(run)

        result = await store.get_run("run-123")
        assert result is not None
        assert result.run_id == "run-123"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self):
        store = InMemoryRunStore()
        result = await store.get_run("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_overwrite(self):
        store = InMemoryRunStore()
        run1 = _make_run("run-1", input_text="v1")
        run2 = _make_run("run-1", input_text="v2")

        await store.save_run(run1)
        await store.save_run(run2)

        result = await store.get_run("run-1")
        assert result.input_text == "v2"


# ── MockRunExecutor ────────────────────────────────────────────────


class TestMockRunExecutor:
    @pytest.mark.asyncio
    async def test_execute(self):
        executor = MockRunExecutor(output_text="mock output")
        output, metadata = await executor.execute("input")
        assert output == "mock output"
        assert metadata == {}

    @pytest.mark.asyncio
    async def test_execute_with_metadata(self):
        executor = MockRunExecutor(
            output_text="output",
            metadata={"duration_ms": 100, "input_tokens": 50},
        )
        output, metadata = await executor.execute("input")
        assert output == "output"
        assert metadata["duration_ms"] == 100


# ── ReplayRunner ───────────────────────────────────────────────────


class TestReplayRunner:
    @pytest.mark.asyncio
    async def test_basic_replay(self):
        store = InMemoryRunStore()
        run = _make_run()
        await store.save_run(run)

        executor = MockRunExecutor(output_text="new output")
        runner = ReplayRunner(store, executor)

        result = await runner.replay("run-123")

        assert result.original_run_id == "run-123"
        assert result.new_run_id
        assert result.original_run.input_text == "What is AI?"
        assert result.new_run.output_text == "new output"
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_replay_preserves_input(self):
        store = InMemoryRunStore()
        run = _make_run(input_text="What is ML?")
        await store.save_run(run)

        executor = MockRunExecutor(output_text="ML is...")
        runner = ReplayRunner(store, executor)

        result = await runner.replay("run-123")

        assert result.new_run.input_text == "What is ML?"

    @pytest.mark.asyncio
    async def test_replay_nonexistent_run(self):
        store = InMemoryRunStore()
        executor = MockRunExecutor()
        runner = ReplayRunner(store, executor)

        result = await runner.replay("nonexistent")

        assert result.error_message is not None
        assert "not found" in result.error_message

    @pytest.mark.asyncio
    async def test_replay_with_config(self):
        store = InMemoryRunStore()
        run = _make_run()
        await store.save_run(run)

        executor = MockRunExecutor(output_text="output")
        runner = ReplayRunner(store, executor)

        config = ReplayConfig(target_name="Agent v2")
        result = await runner.replay("run-123", config)

        assert result.new_run.agent_key == "Agent v2"

    @pytest.mark.asyncio
    async def test_replay_saves_new_run(self):
        store = InMemoryRunStore()
        run = _make_run()
        await store.save_run(run)

        executor = MockRunExecutor(output_text="new output")
        runner = ReplayRunner(store, executor)

        result = await runner.replay("run-123")

        # 新 Run 应该被保存
        new_run = await store.get_run(result.new_run_id)
        assert new_run is not None
        assert new_run.output_text == "new output"

    @pytest.mark.asyncio
    async def test_replay_with_evaluator(self):
        store = InMemoryRunStore()
        run = _make_run()
        await store.save_run(run)

        executor = MockRunExecutor(output_text="new output")
        evaluator = MockEvaluator(score=0.9)
        runner = ReplayRunner(store, executor, evaluator)

        result = await runner.replay("run-123")

        assert result.comparison is not None
        assert result.comparison.baseline_run_id == "run-123"

    @pytest.mark.asyncio
    async def test_replay_executor_error(self):
        store = InMemoryRunStore()
        run = _make_run()
        await store.save_run(run)

        class FailingExecutor:
            async def execute(self, input_text):
                raise RuntimeError("execution failed")

        runner = ReplayRunner(store, FailingExecutor())

        result = await runner.replay("run-123")

        assert result.error_message is not None
        assert "execution failed" in result.error_message

    @pytest.mark.asyncio
    async def test_replay_metadata(self):
        store = InMemoryRunStore()
        run = _make_run()
        await store.save_run(run)

        executor = MockRunExecutor(
            output_text="output",
            metadata={
                "duration_ms": 500,
                "input_tokens": 200,
                "output_tokens": 100,
                "tool_call_count": 2,
                "tool_names": ["search", "calculate"],
            },
        )
        runner = ReplayRunner(store, executor)

        result = await runner.replay("run-123")

        assert result.new_run.duration_ms == 500
        assert result.new_run.total_input_tokens == 200
        assert result.new_run.total_output_tokens == 100
        assert result.new_run.tool_call_count == 2
        assert result.new_run.tool_names == ["search", "calculate"]


# ── Batch Replay ───────────────────────────────────────────────────


class TestBatchReplay:
    @pytest.mark.asyncio
    async def test_replay_batch(self):
        store = InMemoryRunStore()
        await store.save_run(_make_run("run-1"))
        await store.save_run(_make_run("run-2"))

        executor = MockRunExecutor(output_text="output")
        runner = ReplayRunner(store, executor)

        results = await runner.replay_batch(["run-1", "run-2"])

        assert len(results) == 2
        assert results[0].original_run_id == "run-1"
        assert results[1].original_run_id == "run-2"

    @pytest.mark.asyncio
    async def test_replay_batch_empty(self):
        store = InMemoryRunStore()
        executor = MockRunExecutor()
        runner = ReplayRunner(store, executor)

        results = await runner.replay_batch([])

        assert results == []


# ── Replay to Dataset ──────────────────────────────────────────────


class TestReplayToDataset:
    @pytest.mark.asyncio
    async def test_replay_to_dataset(self):
        store = InMemoryRunStore()
        await store.save_run(_make_run("run-1"))
        await store.save_run(_make_run("run-2"))

        executor = MockRunExecutor()
        runner = ReplayRunner(store, executor)

        examples = await runner.replay_to_dataset(
            ["run-1", "run-2"],
            dataset_id="dataset-1",
        )

        assert len(examples) == 2
        assert all(e.dataset_id == "dataset-1" for e in examples)
        assert all("replay" in e.tags for e in examples)

    @pytest.mark.asyncio
    async def test_replay_to_dataset_nonexistent(self):
        store = InMemoryRunStore()
        executor = MockRunExecutor()
        runner = ReplayRunner(store, executor)

        examples = await runner.replay_to_dataset(
            ["nonexistent"],
            dataset_id="dataset-1",
        )

        assert len(examples) == 0
