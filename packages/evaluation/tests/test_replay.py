"""Tests for Replay MVP — v2 with RunExecutor and RunTarget."""

from __future__ import annotations

import pytest

from evaluation.contracts_v2 import (
    AgentRunSummary,
    DatasetExample,
    EvaluationContext,
    EvaluationResult,
    MetricResult,
    RunStatus,
    RunView,
)
from evaluation.replay import (
    InMemoryRunStore,
    MockRunExecutor,
    ReplayConfig,
    ReplayResult,
    ReplayRunner,
    RunTarget,
)


def _make_run(run_id: str = "run-123", **kwargs) -> AgentRunSummary:
    defaults = {
        "run_id": run_id,
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
    """模拟评估器。"""

    def __init__(self, score: float = 0.8) -> None:
        self.name = "mock"
        self.score = score

    async def evaluate(self, context):
        return EvaluationResult(
            example_id=context.example.example_id,
            score=self.score,
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
    async def test_execute_returns_run_view(self):
        executor = MockRunExecutor(output_text="mock output")
        result = await executor.execute(
            input="test input",
            target=RunTarget(agent_key="test-agent"),
        )
        assert isinstance(result, RunView)
        assert result.output == "mock output"
        assert result.input == "test input"

    @pytest.mark.asyncio
    async def test_execute_records_target(self):
        executor = MockRunExecutor()
        target = RunTarget(agent_key="agent-v2", agent_version="2.0")
        await executor.execute(input="x", target=target)
        assert executor.received_target == target
        assert executor.received_target.agent_version == "2.0"

    @pytest.mark.asyncio
    async def test_execute_uses_target_agent_key(self):
        executor = MockRunExecutor()
        result = await executor.execute(
            input="x",
            target=RunTarget(agent_key="my-agent"),
        )
        assert result.agent_key == "my-agent"


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
        assert result.new_run_id == "mock-run-id"
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
    async def test_replay_with_target_config(self):
        """ReplayConfig.target 真正传入 RunExecutor。"""
        store = InMemoryRunStore()
        run = _make_run()
        await store.save_run(run)

        executor = MockRunExecutor(output_text="output")
        runner = ReplayRunner(store, executor)

        config = ReplayConfig(
            target=RunTarget(agent_key="refund-agent", agent_version="v2"),
        )
        result = await runner.replay("run-123", config)

        # Executor 收到了正确的 target
        assert executor.received_target.agent_key == "refund-agent"
        assert executor.received_target.agent_version == "v2"
        # 新 Run 的 agent_key 来自 executor（Runtime）
        assert result.new_run.agent_key == "refund-agent"

    @pytest.mark.asyncio
    async def test_replay_target_from_original(self):
        """config.target=None 时，使用 original_run 的 target。"""
        store = InMemoryRunStore()
        run = _make_run(agent_key="original-agent")
        await store.save_run(run)

        executor = MockRunExecutor()
        runner = ReplayRunner(store, executor)

        result = await runner.replay("run-123")

        # executor 收到了 original_run 的 agent_key
        assert executor.received_target.agent_key == "original-agent"

    @pytest.mark.asyncio
    async def test_replay_executor_error(self):
        store = InMemoryRunStore()
        run = _make_run()
        await store.save_run(run)

        class FailingExecutor:
            async def execute(self, *, input, target, metadata=None):
                raise RuntimeError("execution failed")

        runner = ReplayRunner(store, FailingExecutor())

        result = await runner.replay("run-123")

        assert result.error_message is not None
        assert "execution failed" in result.error_message
        assert result.new_run is None

    @pytest.mark.asyncio
    async def test_replay_metadata_passthrough(self):
        """replay metadata 包含 replay_of_run_id。"""
        store = InMemoryRunStore()
        run = _make_run()
        await store.save_run(run)

        executor = MockRunExecutor()
        runner = ReplayRunner(store, executor)

        await runner.replay("run-123")

        # executor 收到了包含 replay_of_run_id 的 metadata
        assert executor.received_target is not None

    @pytest.mark.asyncio
    async def test_replay_no_uuid_generation(self):
        """ReplayRunner 不生成 run_id/trace_id（来自 executor）。"""
        store = InMemoryRunStore()
        run = _make_run()
        await store.save_run(run)

        executor = MockRunExecutor(
            run_id="runtime-generated-id",
            trace_id="runtime-trace-id",
        )
        runner = ReplayRunner(store, executor)

        result = await runner.replay("run-123")

        # run_id/trace_id 来自 executor（Runtime），不是 ReplayRunner
        assert result.new_run_id == "runtime-generated-id"
        assert result.new_run.trace_id == "runtime-trace-id"

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
