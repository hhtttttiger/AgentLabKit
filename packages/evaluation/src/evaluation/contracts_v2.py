"""Evaluation v2 核心契约。

基于 Execution Model v2 的评估系统：
- DatasetExample: 评估数据集中的一个样本
- Evaluator: 评估器协议
- EvaluationResult: 单次评估结果
- EvaluationContext: 评估上下文（包含 AgentRun + Trace）
- EvaluationRun: 一次完整的评估运行
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable


# ── 数据集 ─────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class DatasetExample:
    """评估数据集中的一个样本。

    替代旧的 EvalCase，与 Execution Model v2 对齐。
    """
    example_id: str
    dataset_id: str
    input_text: str
    expected_output: str | None = None
    context: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)


# ── 评估上下文 ─────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class AgentRunSummary:
    """AgentRun 的摘要，用于评估上下文。"""
    run_id: str
    trace_id: str
    agent_key: str
    input_text: str
    output_text: str
    status: str
    duration_ms: int
    total_input_tokens: int
    total_output_tokens: int
    tool_call_count: int
    tool_names: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SpanSummary:
    """Span 的摘要，用于评估上下文。"""
    span_id: str
    name: str
    kind: str
    duration_ms: int
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvaluationContext:
    """评估上下文 — 包含 AgentRun 和 Trace 信息。

    评估器可以通过此上下文访问完整的执行信息。
    """
    example: DatasetExample
    run: AgentRunSummary | None = None
    spans: list[SpanSummary] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


# ── 评估结果 ───────────────────────────────────────────────────────


class MetricScore(Enum):
    """标准化的评分范围。"""
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"


@dataclass(frozen=True, slots=True)
class MetricResult:
    """单个指标的评估结果。"""
    metric_name: str
    score: float = 0.0        # 0.0 - 1.0
    reasoning: str | None = None
    passed: bool | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """单个样本的评估结果。

    替代旧的 EvalRunResult。
    """
    example_id: str
    run_id: str | None = None
    metric_results: list[MetricResult] = field(default_factory=list)
    overall_score: float = 0.0
    error_message: str | None = None
    duration_ms: int = 0


# ── 评估运行 ───────────────────────────────────────────────────────


class EvaluationRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class EvaluationRun:
    """一次完整的评估运行。

    包含多个 DatasetExample 的评估结果。
    """
    run_id: str
    dataset_id: str
    agent_key: str
    status: EvaluationRunStatus = EvaluationRunStatus.PENDING
    results: list[EvaluationResult] = field(default_factory=list)
    total_examples: int = 0
    completed_examples: int = 0
    failed_examples: int = 0
    overall_score: float = 0.0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


# ── 评估器协议 ─────────────────────────────────────────────────────


@runtime_checkable
class Evaluator(Protocol):
    """评估器协议。

    所有评估器（RAGAS、Agent Native、自定义）都应实现此协议。
    """

    name: str

    async def evaluate(
        self,
        context: EvaluationContext,
    ) -> EvaluationResult:
        """评估单个样本。"""
        ...

    async def evaluate_batch(
        self,
        contexts: list[EvaluationContext],
    ) -> list[EvaluationResult]:
        """批量评估多个样本。"""
        ...


# ── 适配器：旧 → 新 ───────────────────────────────────────────────


def eval_case_to_dataset_example(case: Any) -> DatasetExample:
    """将旧的 EvalCase 转换为 DatasetExample。"""
    return DatasetExample(
        example_id=str(case.id),
        dataset_id=str(case.dataset_id),
        input_text=case.input_text,
        expected_output=case.expected_output,
        context=case.context or [],
        tags=case.tags or [],
        metadata=case.metadata or {},
    )


def eval_run_result_to_evaluation_result(result: Any) -> EvaluationResult:
    """将旧的 EvalRunResult 转换为 EvaluationResult。"""
    metric_results = []
    for mr in result.metric_results:
        metric_results.append(MetricResult(
            metric_name=mr.metric_name,
            score=mr.score,
            reasoning=mr.reasoning,
            passed=mr.passed,
        ))

    return EvaluationResult(
        example_id=str(result.case_id),
        run_id=str(result.run_id) if result.run_id else None,
        metric_results=metric_results,
        overall_score=result.overall_score,
        error_message=result.error_message,
        duration_ms=result.duration_ms,
    )


__all__ = [
    "DatasetExample",
    "AgentRunSummary",
    "SpanSummary",
    "EvaluationContext",
    "MetricScore",
    "MetricResult",
    "EvaluationResult",
    "EvaluationRunStatus",
    "EvaluationRun",
    "Evaluator",
    "eval_case_to_dataset_example",
    "eval_run_result_to_evaluation_result",
]
