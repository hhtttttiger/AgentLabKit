"""DatasetManager — 管理评估数据集。

支持：
- 创建和管理数据集
- 将 Run 转换为 DatasetExample（用于回归测试）
- 批量添加 DatasetExamples

DatasetEvaluationRunner — 通过 RunExecutor 真实执行数据集中的每个 Example。

核心原则：
- DatasetEvaluationRunner 通过 RunExecutor 执行，不自行构造 Run
- EvaluationContext.run 包含真实的 RunView（来自 RunExecutor）
- run_factory: Any 已删除，替换为强类型 RunExecutor
"""

from __future__ import annotations

import logging
import warnings
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
    ExampleEvaluation,
    Expectation,
    SpanSummary,
    TraceProvider,
)
from .replay import RunExecutor, RunTarget

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

    async def add_run(
        self,
        run: Any,
        dataset_id: str,
        *,
        expectations: list[Expectation] | None = None,
        expected_output: Any | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DatasetExample:
        """将 Run 添加为 DatasetExample。

        Args:
            run: RunView or AgentRun
            dataset_id: 目标数据集 ID
            expectations: Agent 行为期望（tool called, trajectory 等）
            expected_output: 期望输出（None 表示使用 run.output）
            tags: 标签
            metadata: 附加 metadata

        Returns:
            创建的 DatasetExample
        """
        example = build_example_from_run(
            run,
            dataset_id=dataset_id,
            expectations=expectations,
            expected_output=expected_output,
            tags=tags,
            metadata=metadata,
        )
        await self._store.add_example(example)
        return example

    async def get_examples(self, dataset_id: str) -> list[DatasetExample]:
        """获取数据集中的所有样本。"""
        return await self._store.get_examples(dataset_id)

    async def run_to_example(
        self,
        run: Any,
        dataset_id: str,
        tags: list[str] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> DatasetExample:
        """将 Run 转换为 DatasetExample（兼容 API）。

        Deprecated: use :meth:`add_run` when persisting a run, or
        :func:`build_example_from_run` for pure conversion.
        """
        warnings.warn(
            "DatasetManager.run_to_example() is deprecated; use add_run() "
            "or build_example_from_run().",
            DeprecationWarning,
            stacklevel=2,
        )
        example = build_example_from_run(
            run,
            dataset_id=dataset_id,
            tags=tags,
            metadata=metadata,
        )
        await self._store.add_example(example)
        return example

    async def run_to_example_with_context(
        self,
        run: Any,
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

        agent_key = getattr(run, "agent_key", "")
        run_id = getattr(run, "run_id", "")
        trace_id = getattr(run, "trace_id", "")
        input_text = getattr(run, "input_text", None) or str(getattr(run, "input", ""))
        output_text = getattr(run, "output_text", None) or str(getattr(run, "output", ""))
        status = getattr(run, "status", "completed")
        duration_ms = getattr(run, "duration_ms", 0)

        example = DatasetExample(
            example_id=uuid4().hex,
            dataset_id=dataset_id,
            input_text=input_text,
            expected_output=output_text,
            context=context_parts,
            tags=tags or ["from_run", f"agent:{agent_key}"],
            metadata={
                "status": str(status),
                "duration_ms": str(duration_ms),
                "span_count": str(len(spans)),
                **(metadata or {}),
            },
            source_run_id=run_id,
            source_trace_id=trace_id,
        )
        await self._store.add_example(example)
        return example


def build_example_from_run(
    run: Any,
    dataset_id: str,
    *,
    expectations: list[Expectation] | None = None,
    expected_output: Any | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> DatasetExample:
    """将 Run 转换为 DatasetExample（纯函数，不写 store）。

    Args:
        run: RunView or AgentRun
        dataset_id: 目标数据集 ID
        expectations: Agent 行为期望
        expected_output: 期望输出（None 使用 run.output）
        tags: 标签
        metadata: 附加 metadata

    Returns:
        DatasetExample（不写入 store）
    """
    agent_key = getattr(run, "agent_key", "")
    run_id = getattr(run, "run_id", "")
    trace_id = getattr(run, "trace_id", "")
    input_text = getattr(run, "input_text", None) or str(getattr(run, "input", ""))
    output_text = getattr(run, "output_text", None) or str(getattr(run, "output", ""))

    return DatasetExample(
        example_id=uuid4().hex,
        dataset_id=dataset_id,
        input_text=input_text,
        expected_output=expected_output if expected_output is not None else output_text,
        context=[],
        tags=tags or ["from_run", f"agent:{agent_key}"],
        metadata=metadata or {},
        expectations=expectations or [],
        source_run_id=run_id,
        source_trace_id=trace_id if trace_id else None,
    )


class DatasetEvaluationRunner:
    """数据集评估运行器。

    通过 RunExecutor 真实执行数据集中的每个 Example，
    然后用 Evaluator 评估结果。

    数据流：
        DatasetExample → RunExecutor → AgentRun → EvaluationContext → Evaluator

    核心原则：
    - run_factory: Any 已删除，替换为 RunExecutor
    - EvaluationContext.run 包含真实 RunView
    - Agent-native evaluator 可以看到真实 trace/span
    """

    def __init__(
        self,
        evaluator: Evaluator,
        store: DatasetStore,
        run_executor: RunExecutor | None = None,
        target: RunTarget | None = None,
        trace_provider: TraceProvider | None = None,
    ) -> None:
        self._evaluator = evaluator
        self._store = store
        self._run_executor = run_executor
        self._target = target or RunTarget()
        self._trace_provider = trace_provider

    async def run(
        self,
        dataset_id: str,
        agent_key: str,
    ) -> EvaluationRun:
        """对数据集运行评估。

        Args:
            dataset_id: 数据集 ID
            agent_key: Agent 标识

        Returns:
            EvaluationRun 包含所有 example 的评估结果
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
                # 如果有 RunExecutor，真实执行
                run_view = None
                if self._run_executor is not None:
                    run_view = await self._run_executor.execute(
                        input=example.input_text,
                        target=self._target,
                    )

                # Fetch trace spans if TraceProvider is available
                spans: list[SpanSummary] = []
                if self._trace_provider is not None and run_view is not None:
                    try:
                        # Trace storage is keyed by trace identity, not the
                        # business Run id. A missing trace remains an empty
                        # context so trace-aware evaluators can skip explicitly.
                        if run_view.trace_id:
                            fetched = await self._trace_provider.get_spans(run_view.trace_id)
                            if fetched is not None:
                                spans = fetched
                    except Exception:
                        logger.exception("trace_provider.get_spans_failed trace_id=%s", run_view.trace_id)

                # 构建评估上下文（包含真实 Run + Spans）
                context = EvaluationContext(
                    example=example,
                    run=run_view,
                    spans=spans,
                    extra={
                        "trace_unavailable": run_view is None or not spans,
                    },
                )

                # 运行评估
                result = await self._evaluator.evaluate(context)
                results.append(result)

                # Returning an EvaluationResult means the evaluator ran to
                # completion.  Its message/skip_reason/passed value describes
                # the evaluated example, not runner orchestration failure.
                completed += 1

            except Exception as e:
                logger.exception("dataset_eval.error example_id=%s", example.example_id)
                results.append(EvaluationResult(
                    example_id=example.example_id,
                    message=str(e),
                ))
                failed += 1

        # 计算总体分数
        # Include scores from PASS and rule FAIL results.  Results without a
        # score (for example SKIPPED) do not contribute to the average.
        scores = [r.overall_score for r in results if r.score is not None or r.metric_results]
        overall_score = sum(scores) / len(scores) if scores else 0.0

        # 更新运行状态
        status = EvaluationRunStatus.COMPLETED if failed == 0 else EvaluationRunStatus.FAILED

        # Build example_evaluations (canonical aggregation by example_id)
        example_eval_map: dict[str, list[EvaluationResult]] = {}
        for r in results:
            example_eval_map.setdefault(r.example_id, []).append(r)
        example_evaluations = [
            ExampleEvaluation(
                example_id=eid,
                results=eresults,
            )
            for eid, eresults in example_eval_map.items()
        ]

        return EvaluationRun(
            run_id=eval_run.run_id,
            dataset_id=dataset_id,
            agent_key=agent_key,
            status=status,
            example_evaluations=example_evaluations,
            total_examples=len(examples),
            completed_examples=completed,
            failed_examples=failed,
            overall_score=round(overall_score, 4),
            started_at=eval_run.started_at,
            completed_at=datetime.now(timezone.utc),
        )


def run_to_example(
    run: Any,
    dataset_id: str,
    *,
    expectations: list[Expectation] | None = None,
    expected_output: Any | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> DatasetExample:
    """Deprecated compatibility alias for :func:`build_example_from_run`."""
    warnings.warn(
        "run_to_example() is deprecated; use build_example_from_run().",
        DeprecationWarning,
        stacklevel=2,
    )
    return build_example_from_run(
        run,
        dataset_id,
        expectations=expectations,
        expected_output=expected_output,
        tags=tags,
        metadata=metadata,
    )


__all__ = [
    "DatasetStore",
    "InMemoryDatasetStore",
    "DatasetManager",
    "DatasetEvaluationRunner",
    "build_example_from_run",
    "run_to_example",
]
