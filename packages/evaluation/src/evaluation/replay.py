"""Replay MVP — 重放历史 Run 以进行回归测试。

支持：
1. 从历史 Run 提取输入
2. 对新目标重放
3. 生成新的 Run 结果
4. 与原始 Run 比较

核心原则：
- ReplayRunner 不生成 run_id / trace_id（Runtime 通过 RunExecutor 拥有）
- ReplayRunner 不构造 AgentRunSummary（RunExecutor 返回 RunView）
- ReplayConfig.target 使用 RunTarget 而非字符串 label
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from .compare import ComparisonResult, compare_runs
from .contracts_v2 import (
    AgentRunSummary,
    DatasetExample,
    EvaluationContext,
    EvaluationResult,
    EvaluationRun,
    EvaluationRunStatus,
    Evaluator,
    RunStatus,
    RunView,
)

logger = logging.getLogger(__name__)


# ── RunTarget (lightweight, for evaluation layer) ────────────────────


@dataclass(frozen=True, slots=True)
class RunTarget:
    """执行目标 — 描述 replay 应该对哪个 agent/version 执行。

    与 agent_runtime.contracts.run.RunTarget 对齐，但 evaluation 层
    不直接依赖 agent_runtime，所以独立定义。
    """

    type: str = "agent"
    agent_key: str | None = None
    agent_version: str | None = None
    workflow_id: str | None = None
    workflow_version: str | None = None


# ── Protocols ────────────────────────────────────────────────────────


@runtime_checkable
class RunStore(Protocol):
    """Run 存储协议。"""

    async def get_run(self, run_id: str) -> RunView | None:
        """获取历史 Run。"""
        ...

    async def save_run(self, run: RunView) -> None:
        """保存 Run。"""
        ...


@runtime_checkable
class RunExecutor(Protocol):
    """Run 执行器协议 — Runtime adapter 实现此协议。

    execute 接收输入和目标，委托给 AgentRuntime.run()，
    返回 Runtime 产生的 RunView（包含 Runtime 创建的 run_id/trace_id）。

    ReplayRunner 通过此协议调用 Runtime，绝不自行构造 Run。
    """

    async def execute(
        self,
        *,
        input: Any,
        target: RunTarget,
        metadata: dict[str, Any] | None = None,
    ) -> RunView:
        """执行目标并返回 Runtime 产生的 RunView。"""
        ...


# ── Config ───────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ReplayConfig:
    """重放配置。

    target: 执行目标。None 表示使用 original_run 的 target。
    metadata: 附加 metadata，会与 original metadata 合并。
    example_id: DatasetExample 的 stable identity。用于 replay compare 时
        baseline/candidate 对齐同一个 example。None 时回退到 original.run_id。
    """

    target: RunTarget | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    example_id: str | None = None


# ── Result ───────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ReplayResult:
    """重放结果。"""
    original_run_id: str
    new_run_id: str
    original_run: RunView | None
    new_run: RunView | None
    comparison: ComparisonResult | None = None
    duration_ms: int = 0
    error_message: str | None = None
    example_id: str | None = None


# ── Runner ───────────────────────────────────────────────────────────


class ReplayRunner:
    """重放运行器。

    职责：
    1. 读取旧 Run（通过 RunStore）
    2. 构造 ReplayConfig（target 来源）
    3. 调用 RunExecutor 执行（Runtime 产生新 Run）
    4. 返回 ReplayResult

    禁止：
    - 生成 run_id / trace_id
    - 构造 AgentRunSummary
    - 直接调用 AgentRuntime
    """

    def __init__(
        self,
        run_store: RunStore,
        executor: RunExecutor,
        evaluator: Evaluator | None = None,
    ) -> None:
        self._run_store = run_store
        self._executor = executor
        self._evaluator = evaluator

    async def replay(
        self,
        run_id: str,
        config: ReplayConfig | None = None,
    ) -> ReplayResult:
        """重放一个历史 Run。

        Args:
            run_id: 历史 Run ID
            config: 重放配置（target 等）

        Returns:
            ReplayResult 包含原始 Run 和新 Run
        """
        import time
        config = config or ReplayConfig()
        start = time.monotonic()

        # 1. 获取历史 Run
        original_run = await self._run_store.get_run(run_id)
        if original_run is None:
            return ReplayResult(
                original_run_id=run_id,
                new_run_id="",
                original_run=None,
                new_run=None,
                error_message=f"run {run_id} not found",
                duration_ms=int((time.monotonic() - start) * 1000),
            )

        # 2. 确定 target：config.target or original_run 的 target
        # When no config.target, preserve the original run's target
        # (including agent_version for faithful replay)
        original_target = getattr(original_run, "target", None)
        if config.target:
            target = config.target
        elif original_target is not None:
            target = RunTarget(
                type=getattr(original_target, "type", "agent") or "agent",
                agent_key=getattr(original_target, "agent_key", None) or "",
                agent_version=getattr(original_target, "agent_version", None),
            )
        else:
            target = RunTarget(
                type="agent",
                agent_key=getattr(original_run, "agent_key", None) or "",
            )

        # 3. 构造 metadata
        merged_metadata = {
            "replay_of_run_id": run_id,
            **config.metadata,
        }

        # 4. 调用 RunExecutor（Runtime 产生新 Run，包含 run_id/trace_id）
        try:
            new_run = await self._executor.execute(
                input=original_run.input,
                target=target,
                metadata=merged_metadata,
            )
        except Exception as e:
            logger.exception("replay.failed run_id=%s", run_id)
            return ReplayResult(
                original_run_id=run_id,
                new_run_id="",
                original_run=original_run,
                new_run=None,
                error_message=str(e),
                duration_ms=int((time.monotonic() - start) * 1000),
            )

        # 5. 比较（如果配置了评估器）
        comparison = None
        if self._evaluator is not None:
            comparison = await self._compare_runs(
                original_run, new_run,
                example_id=config.example_id,
            )

        return ReplayResult(
            original_run_id=run_id,
            new_run_id=new_run.run_id,
            original_run=original_run,
            new_run=new_run,
            comparison=comparison,
            duration_ms=int((time.monotonic() - start) * 1000),
            example_id=config.example_id,
        )

    async def replay_batch(
        self,
        run_ids: list[str],
        config: ReplayConfig | None = None,
    ) -> list[ReplayResult]:
        """批量重放多个历史 Run。"""
        results = []
        for run_id in run_ids:
            result = await self.replay(run_id, config)
            results.append(result)
        return results

    async def _compare_runs(
        self,
        original: RunView,
        new: RunView,
        *,
        example_id: str | None = None,
    ) -> ComparisonResult:
        """比较原始 Run 和新 Run。

        baseline 和 candidate 使用同一个 example_id，
        这样 compare_runs 可以正确对齐。

        Args:
            original: 原始 Run
            new: 新 Run
            example_id: DatasetExample 的 stable identity。
                None 时回退到 original.run_id。
        """
        shared_example_id = example_id or original.run_id

        original_context = EvaluationContext(
            example=DatasetExample(
                example_id=shared_example_id,
                dataset_id="replay",
                input_text=str(original.input),
                expected_output=str(original.output) if original.output else None,
            ),
            run=original,
        )

        new_context = EvaluationContext(
            example=DatasetExample(
                example_id=shared_example_id,
                dataset_id="replay",
                input_text=str(new.input),
                expected_output=str(new.output) if new.output else None,
            ),
            run=new,
        )

        original_result = await self._evaluator.evaluate(original_context)
        new_result = await self._evaluator.evaluate(new_context)

        # 构建 EvaluationRun 用于比较（同一个 dataset_id）
        original_eval_run = EvaluationRun(
            run_id=original.run_id,
            dataset_id="replay",
            agent_key=getattr(original, "agent_key", ""),
            status=EvaluationRunStatus.COMPLETED,
            results=[original_result],
            total_examples=1,
            completed_examples=1,
        )

        new_eval_run = EvaluationRun(
            run_id=new.run_id,
            dataset_id="replay",
            agent_key=getattr(new, "agent_key", ""),
            status=EvaluationRunStatus.COMPLETED,
            results=[new_result],
            total_examples=1,
            completed_examples=1,
        )

        return compare_runs(original_eval_run, new_eval_run)


# ── In-memory implementations (for testing) ──────────────────────────


class InMemoryRunStore:
    """内存 Run 存储（用于测试）。"""

    def __init__(self) -> None:
        self._runs: dict[str, RunView] = {}

    async def get_run(self, run_id: str) -> RunView | None:
        return self._runs.get(run_id)

    async def save_run(self, run: RunView) -> None:
        self._runs[run.run_id] = run


class MockRunExecutor:
    """模拟 Run 执行器（用于测试）。

    返回一个 AgentRunSummary 作为 RunView，run_id/trace_id 由本 mock 生成。
    真实的 RunExecutor 实现应委托给 AgentRuntime.run()，
    由 Runtime 创建 identity。
    """

    def __init__(
        self,
        output_text: str = "mock output",
        run_id: str = "mock-run-id",
        trace_id: str = "mock-trace-id",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.output_text = output_text
        self.run_id = run_id
        self.trace_id = trace_id
        self.metadata = metadata or {}
        self.received_target: RunTarget | None = None

    async def execute(
        self,
        *,
        input: Any,
        target: RunTarget,
        metadata: dict[str, Any] | None = None,
    ) -> RunView:
        self.received_target = target
        return AgentRunSummary(
            run_id=self.run_id,
            trace_id=self.trace_id,
            agent_key=target.agent_key or "",
            input_text=str(input),
            output_text=self.output_text,
            status=RunStatus.COMPLETED,
            duration_ms=self.metadata.get("duration_ms", 0),
            total_input_tokens=self.metadata.get("input_tokens", 0),
            total_output_tokens=self.metadata.get("output_tokens", 0),
            tool_call_count=self.metadata.get("tool_call_count", 0),
            tool_names=self.metadata.get("tool_names", []),
        )


__all__ = [
    "RunTarget",
    "RunStore",
    "RunExecutor",
    "ReplayConfig",
    "ReplayResult",
    "ReplayRunner",
    "InMemoryRunStore",
    "MockRunExecutor",
]
