"""DatasetManager — 管理评估数据集。

支持：
- 创建和管理数据集
- 将 Run 转换为 DatasetExample（用于回归测试）
- 批量添加 DatasetExamples
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

from .contracts_v2 import (
    AgentRunSummary,
    DatasetExample,
    EvaluationContext,
    EvaluationResult,
    EvaluationRun,
    EvaluationRunStatus,
    Evaluator,
    SpanSummary,
)

logger = logging.getLogger(__name__)


@runtime_checkable
class DatasetStore(Protocol):
    """数据集存储协议。"""

    async def create_dataset(self, name: str, description: str | None = None) -> str:
        """创建数据集，返回 dataset_id。"""
        ...

    async def add_example(self, example: DatasetExample) -> None:
        """添加样本到数据集。"""
        ...

    async def get_examples(self, dataset_id: str) -> list[DatasetExample]:
        """获取数据集中的所有样本。"""
        ...

    async def delete_example(self, example_id: str) -> None:
        """删除样本。"""
        ...


class InMemoryDatasetStore:
    """内存数据集存储（用于测试）。"""

    def __init__(self) -> None:
        self._datasets: dict[str, dict[str, Any]] = {}
        self._examples: dict[str, DatasetExample] = {}

    async def create_dataset(self, name: str, description: str | None = None) -> str:
        dataset_id = uuid4().hex
        self._datasets[dataset_id] = {
            "name": name,
            "description": description,
            "created_at": datetime.now(timezone.utc),
        }
        return dataset_id

    async def add_example(self, example: DatasetExample) -> None:
        self._examples[example.example_id] = example

    async def get_examples(self, dataset_id: str) -> list[DatasetExample]:
        return [e for e in self._examples.values() if e.dataset_id == dataset_id]

    async def delete_example(self, example_id: str) -> None:
        self._examples.pop(example_id, None)


class DatasetManager:
    """数据集管理器。

    提供高级 API 来管理评估数据集，
    包括将 Run 转换为 DatasetExample 的功能。
    """

    def __init__(self, store: DatasetStore) -> None:
        self._store = store

    async def create_dataset(self, name: str, description: str | None = None) -> str:
        """创建新数据集。"""
        return await self._store.create_dataset(name, description)

    async def add_example(self, example: DatasetExample) -> None:
        """添加样本到数据集。"""
        await self._store.add_example(example)

    async def add_examples(self, examples: list[DatasetExample]) -> None:
        """批量添加样本。"""
        for example in examples:
            await self._store.add_example(example)

    async def get_examples(self, dataset_id: str) -> list[DatasetExample]:
        """获取数据集中的所有样本。"""
        return await self._store.get_examples(dataset_id)

    async def run_to_example(
        self,
        run: AgentRunSummary,
        dataset_id: str,
        tags: list[str] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> DatasetExample:
        """将 Run 转换为 DatasetExample。

        用于将失败的 Run 变成永久 regression case。
        """
        example = DatasetExample(
            example_id=uuid4().hex,
            dataset_id=dataset_id,
            input_text=run.input_text,
            expected_output=run.output_text,
            context=[],  # 可以后续从 spans 中提取
            tags=tags or ["from_run", f"agent:{run.agent_key}"],
            metadata={
                "run_id": run.run_id,
                "trace_id": run.trace_id,
                "status": run.status,
                "duration_ms": str(run.duration_ms),
                **(metadata or {}),
            },
        )
        await self._store.add_example(example)
        return example

    async def run_to_example_with_context(
        self,
        run: AgentRunSummary,
        spans: list[SpanSummary],
        dataset_id: str,
        tags: list[str] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> DatasetExample:
        """将 Run 和其 Spans 转换为 DatasetExample。

        包含执行上下文，可用于更精确的回归测试。
        """
        # 从 spans 中提取有用的上下文
        context_parts = []
        for span in spans:
            if span.name.startswith("tool."):
                tool_name = span.attributes.get("tool.name", "")
                if tool_name:
                    context_parts.append(f"Tool used: {tool_name}")

        example = DatasetExample(
            example_id=uuid4().hex,
            dataset_id=dataset_id,
            input_text=run.input_text,
            expected_output=run.output_text,
            context=context_parts,
            tags=tags or ["from_run", f"agent:{run.agent_key}"],
            metadata={
                "run_id": run.run_id,
                "trace_id": run.trace_id,
                "status": run.status,
                "duration_ms": str(run.duration_ms),
                "span_count": str(len(spans)),
                **(metadata or {}),
            },
        )
        await self._store.add_example(example)
        return example


class DatasetEvaluationRunner:
    """数据集评估运行器。

    对一个数据集运行评估，生成 EvaluationRun。
    """

    def __init__(
        self,
        evaluator: Evaluator,
        store: DatasetStore,
    ) -> None:
        self._evaluator = evaluator
        self._store = store

    async def run(
        self,
        dataset_id: str,
        agent_key: str,
        run_factory: Any | None = None,
    ) -> EvaluationRun:
        """对数据集运行评估。

        Args:
            dataset_id: 数据集 ID
            agent_key: Agent 标识
            run_factory: 可选的运行工厂，用于生成 AgentRunSummary
        """
        import time
        start = time.monotonic()

        # 获取数据集样本
        examples = await self._store.get_examples(dataset_id)
        if not examples:
            return EvaluationRun(
                run_id=uuid4().hex,
                dataset_id=dataset_id,
                agent_key=agent_key,
                status=EvaluationRunStatus.FAILED,
                error_message="dataset is empty",
                total_examples=0,
            )

        # 创建评估运行
        eval_run = EvaluationRun(
            run_id=uuid4().hex,
            dataset_id=dataset_id,
            agent_key=agent_key,
            status=EvaluationRunStatus.RUNNING,
            total_examples=len(examples),
            started_at=datetime.now(timezone.utc),
        )

        results: list[EvaluationResult] = []
        completed = 0
        failed = 0

        # 逐个评估
        for example in examples:
            try:
                # 构建评估上下文
                context = EvaluationContext(
                    example=example,
                    # 如果有 run_factory，可以生成 AgentRunSummary
                )

                # 运行评估
                result = await self._evaluator.evaluate(context)
                results.append(result)

                if result.error_message:
                    failed += 1
                else:
                    completed += 1

            except Exception as e:
                logger.exception("dataset_eval.error example_id=%s", example.example_id)
                results.append(EvaluationResult(
                    example_id=example.example_id,
                    message=str(e),
                ))
                failed += 1

        # 计算总体分数
        scores = [r.overall_score for r in results if r.error_message is None]
        overall_score = sum(scores) / len(scores) if scores else 0.0

        # 更新运行状态
        status = EvaluationRunStatus.COMPLETED if failed == 0 else EvaluationRunStatus.FAILED

        return EvaluationRun(
            run_id=eval_run.run_id,
            dataset_id=dataset_id,
            agent_key=agent_key,
            status=status,
            results=results,
            total_examples=len(examples),
            completed_examples=completed,
            failed_examples=failed,
            overall_score=round(overall_score, 4),
            started_at=eval_run.started_at,
            completed_at=datetime.now(timezone.utc),
        )


__all__ = [
    "DatasetStore",
    "InMemoryDatasetStore",
    "DatasetManager",
    "DatasetEvaluationRunner",
]
