"""Replay MVP — 重放历史 Run 以进行回归测试。

支持：
1. 从历史 Run 提取输入
2. 对新目标重放
3. 生成新的 Run 结果
4. 与原始 Run 比较
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

from .compare import ComparisonResult, compare_runs
from .contracts_v2 import (
    AgentRunSummary,
    DatasetExample,
    EvaluationContext,
    EvaluationResult,
    EvaluationRun,
    EvaluationRunStatus,
    Evaluator,
)

logger = logging.getLogger(__name__)


@runtime_checkable
class RunStore(Protocol):
    """Run 存储协议。"""

    async def get_run(self, run_id: str) -> AgentRunSummary | None:
        """获取历史 Run。"""
        ...

    async def save_run(self, run: AgentRunSummary) -> None:
        """保存 Run。"""
        ...


@runtime_checkable
class RunExecutor(Protocol):
    """Run 执行器协议。

    用于重放 Run — 接收输入，执行目标，返回输出。
    """

    async def execute(self, input_text: str) -> tuple[str, dict[str, Any]]:
        """执行目标并返回 (output_text, metadata)。"""
        ...


@dataclass(frozen=True, slots=True)
class ReplayConfig:
    """重放配置。"""
    target_name: str = ""          # 目标名称（如 "Agent v2"）
    preserve_metadata: bool = True # 是否保留原始 metadata
    timeout_seconds: int = 300     # 超时时间


@dataclass(frozen=True, slots=True)
class ReplayResult:
    """重放结果。"""
    original_run_id: str
    new_run_id: str
    original_run: AgentRunSummary
    new_run: AgentRunSummary
    comparison: ComparisonResult | None = None
    duration_ms: int = 0
    error_message: str | None = None


class ReplayRunner:
    """重放运行器。

    从历史 Run 提取输入，对新目标重放，生成新的 Run。
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
            config: 重放配置

        Returns:
            ReplayResult 包含原始 Run 和新 Run 的比较结果
        """
        config = config or ReplayConfig()
        start = time.monotonic()

        # 1. 获取历史 Run
        original_run = await self._run_store.get_run(run_id)
        if original_run is None:
            return ReplayResult(
                original_run_id=run_id,
                new_run_id="",
                original_run=_empty_run(),
                new_run=_empty_run(),
                error_message=f"run {run_id} not found",
                duration_ms=int((time.monotonic() - start) * 1000),
            )

        # 2. 重放
        try:
            new_run_id = uuid4().hex
            output_text, metadata = await self._executor.execute(original_run.input_text)

            # 3. 构建新 Run
            new_run = AgentRunSummary(
                run_id=new_run_id,
                trace_id=uuid4().hex,
                agent_key=config.target_name or original_run.agent_key,
                input_text=original_run.input_text,
                output_text=output_text,
                status="ok",
                duration_ms=metadata.get("duration_ms", 0),
                total_input_tokens=metadata.get("input_tokens", 0),
                total_output_tokens=metadata.get("output_tokens", 0),
                tool_call_count=metadata.get("tool_call_count", 0),
                tool_names=metadata.get("tool_names", []),
            )

            # 4. 保存新 Run
            await self._run_store.save_run(new_run)

            # 5. 比较（如果配置了评估器）
            comparison = None
            if self._evaluator is not None:
                comparison = await self._compare_runs(original_run, new_run)

            return ReplayResult(
                original_run_id=run_id,
                new_run_id=new_run_id,
                original_run=original_run,
                new_run=new_run,
                comparison=comparison,
                duration_ms=int((time.monotonic() - start) * 1000),
            )

        except Exception as e:
            logger.exception("replay.failed run_id=%s", run_id)
            return ReplayResult(
                original_run_id=run_id,
                new_run_id="",
                original_run=original_run,
                new_run=_empty_run(),
                error_message=str(e),
                duration_ms=int((time.monotonic() - start) * 1000),
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

    async def replay_to_dataset(
        self,
        run_ids: list[str],
        dataset_id: str,
        config: ReplayConfig | None = None,
    ) -> list[DatasetExample]:
        """将重放结果转换为 DatasetExamples。

        用于创建回归测试数据集。
        """
        from .dataset import DatasetManager, InMemoryDatasetStore

        store = InMemoryDatasetStore()
        manager = DatasetManager(store)

        examples = []
        for run_id in run_ids:
            original_run = await self._run_store.get_run(run_id)
            if original_run is None:
                continue

            example = await manager.run_to_example(
                original_run,
                dataset_id,
                tags=["replay", f"original_run:{run_id}"],
            )
            examples.append(example)

        return examples

    async def _compare_runs(
        self,
        original: AgentRunSummary,
        new: AgentRunSummary,
    ) -> ComparisonResult:
        """比较原始 Run 和新 Run。"""
        # 对两个 Run 运行评估器
        original_context = EvaluationContext(
            example=DatasetExample(
                example_id=original.run_id,
                dataset_id="replay",
                input_text=original.input_text,
                expected_output=original.output_text,
            ),
            run=original,
        )

        new_context = EvaluationContext(
            example=DatasetExample(
                example_id=new.run_id,
                dataset_id="replay",
                input_text=new.input_text,
                expected_output=new.output_text,
            ),
            run=new,
        )

        original_result = await self._evaluator.evaluate(original_context)
        new_result = await self._evaluator.evaluate(new_context)

        # 构建 EvaluationRun 用于比较
        from .contracts_v2 import EvaluationRun, EvaluationRunStatus

        original_eval_run = EvaluationRun(
            run_id=original.run_id,
            dataset_id="replay",
            agent_key=original.agent_key,
            status=EvaluationRunStatus.COMPLETED,
            results=[original_result],
            total_examples=1,
            completed_examples=1,
        )

        new_eval_run = EvaluationRun(
            run_id=new.run_id,
            dataset_id="replay",
            agent_key=new.agent_key,
            status=EvaluationRunStatus.COMPLETED,
            results=[new_result],
            total_examples=1,
            completed_examples=1,
        )

        return compare_runs(original_eval_run, new_eval_run)


def _empty_run() -> AgentRunSummary:
    return AgentRunSummary(
        run_id="",
        trace_id="",
        agent_key="",
        input_text="",
        output_text="",
        status="error",
        duration_ms=0,
        total_input_tokens=0,
        total_output_tokens=0,
        tool_call_count=0,
    )


class InMemoryRunStore:
    """内存 Run 存储（用于测试）。"""

    def __init__(self) -> None:
        self._runs: dict[str, AgentRunSummary] = {}

    async def get_run(self, run_id: str) -> AgentRunSummary | None:
        return self._runs.get(run_id)

    async def save_run(self, run: AgentRunSummary) -> None:
        self._runs[run.run_id] = run


class MockRunExecutor:
    """模拟 Run 执行器（用于测试）。"""

    def __init__(
        self,
        output_text: str = "mock output",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.output_text = output_text
        self.metadata = metadata or {}

    async def execute(self, input_text: str) -> tuple[str, dict[str, Any]]:
        return self.output_text, self.metadata


__all__ = [
    "RunStore",
    "RunExecutor",
    "ReplayConfig",
    "ReplayResult",
    "ReplayRunner",
    "InMemoryRunStore",
    "MockRunExecutor",
]
