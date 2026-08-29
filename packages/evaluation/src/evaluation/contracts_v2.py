"""Evaluation v2 核心契约。

基于 Execution Model v2 的评估系统：
- DatasetExample: 评估数据集中的一个样本（含 expectations）
- Evaluator: 评估器协议
- EvaluationResult: 单次评估结果
- EvaluationContext: 评估上下文（包含 RunView + Spans）
- EvaluationRun: 一次完整的评估运行
- RunView: Run 的评估投影协议
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable


# ── Run status (6.6: 复用共享枚举) ─────────────────────────────────


class RunStatus(str, Enum):
    """Run 状态枚举 — 与 agent_runtime.contracts.run.RunStatus 对齐。"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ── Expectations (6.1) ─────────────────────────────────────────────


class ExpectationType(str, Enum):
    """Expectation 类型 — 描述 Agent 行为的期望。"""
    TOOL_CALLED = "tool_called"
    TOOL_NOT_CALLED = "tool_not_called"
    TOOL_ARGUMENTS = "tool_arguments"
    EXPECTED_TRAJECTORY = "expected_trajectory"
    OUTPUT_CONTAINS = "output_contains"
    OUTPUT_SCHEMA = "output_schema"
    MAX_STEPS = "max_steps"


@dataclass(frozen=True, slots=True)
class Expectation:
    """单个期望 — 数据描述，不是执行逻辑。

    Expectation 是数据描述，Evaluator 是执行逻辑，两者不要混在一起。
    """
    type: ExpectationType
    value: Any = None
    description: str | None = None


# ── RunView (6.7) ──────────────────────────────────────────────────


@runtime_checkable
class RunView(Protocol):
    """Run 的评估投影 — Evaluation 只依赖此协议。

    避免 Runtime AgentRun 与 Evaluation AgentRunSummary 两套模型持续漂移。
    """

    @property
    def run_id(self) -> str: ...

    @property
    def trace_id(self) -> str | None: ...

    @property
    def input(self) -> Any: ...

    @property
    def output(self) -> Any | None: ...

    @property
    def status(self) -> RunStatus: ...

    @property
    def started_at(self) -> datetime: ...

    @property
    def finished_at(self) -> datetime | None: ...


# ── AgentRunSummary (concrete RunView implementation) ───────────────


@dataclass(frozen=True, slots=True)
class AgentRunSummary:
    """AgentRun 的摘要，用于评估上下文。

    实现 RunView 协议。保留向后兼容。
    """
    run_id: str
    trace_id: str = ""
    agent_key: str = ""
    input_text: str = ""
    output_text: str = ""
    status: str = "completed"
    duration_ms: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    tool_call_count: int = 0
    tool_names: list[str] = field(default_factory=list)

    # RunView protocol properties
    @property
    def input(self) -> str:
        return self.input_text

    @property
    def output(self) -> str | None:
        return self.output_text

    @property
    def started_at(self) -> datetime:
        return datetime.now()  # placeholder

    @property
    def finished_at(self) -> datetime | None:
        return None  # placeholder


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
    metadata: dict[str, Any] = field(default_factory=dict)

    # 6.1: expectations 是 Agent-native Dataset 的核心能力
    expectations: list[Expectation] = field(default_factory=list)

    # 6.2: source_run_id 升级为一等字段
    source_run_id: str | None = None
    source_trace_id: str | None = None


# ── 评估上下文 ─────────────────────────────────────────────────────


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
    """评估上下文 — 包含 DatasetExample 和可选的 Run + Spans。

    评估器可以通过此上下文访问完整的执行信息。
    允许纯 output evaluator 在没有 trace 时工作，
    但 Agent-native evaluation 不能缺 Run。
    """
    example: DatasetExample
    run: RunView | None = None
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
    """单个指标的评估结果（向后兼容）。"""
    metric_name: str
    score: float = 0.0        # 0.0 - 1.0
    reasoning: str | None = None
    passed: bool | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """单个样本的评估结果 (6.5)。

    替代旧的 EvalRunResult。
    """
    evaluator_name: str = ""
    evaluator_version: str | None = None

    example_id: str = ""
    run_id: str | None = None

    passed: bool | None = None
    score: float | None = None       # 6.4: None 表示没有 score，不是 0
    label: str | None = None

    message: str | None = None

    details: dict[str, Any] = field(default_factory=dict)

    # 向后兼容：metric_results
    metric_results: list[MetricResult] = field(default_factory=list)

    duration_ms: int = 0

    # 向后兼容：overall_score property
    @property
    def overall_score(self) -> float:
        if self.score is not None:
            return self.score
        if self.metric_results:
            scores = [r.score for r in self.metric_results]
            return sum(scores) / len(scores) if scores else 0.0
        return 0.0

    # 向后兼容：error_message property
    @property
    def error_message(self) -> str | None:
        return self.message


# ── 评估运行 ───────────────────────────────────────────────────────


class EvaluationRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class ExampleEvaluation:
    """一个 example 的多 evaluator 聚合结果 (7.3)。

    多个 evaluator 对同一个 example 的结果聚合。
    """
    example_id: str = ""
    run_id: str | None = None
    trace_id: str | None = None
    results: list[EvaluationResult] = field(default_factory=list)

    @property
    def passed(self) -> bool | None:
        """所有 evaluator 都通过则 True，有失败则 False，否则 None。"""
        passed_results = [r.passed for r in self.results if r.passed is not None]
        if not passed_results:
            return None
        return all(passed_results)

    @property
    def all_passed(self) -> bool:
        """所有评估器都通过。"""
        return all(r.passed for r in self.results if r.passed is not None)

    @property
    def any_failed(self) -> bool:
        """任意评估器失败。"""
        return any(not r.passed for r in self.results if r.passed is not None)

    @property
    def average_score(self) -> float | None:
        """所有有 score 的 evaluator 的平均分。"""
        scores = [r.score for r in self.results if r.score is not None]
        if not scores:
            return None
        return sum(scores) / len(scores)

    @property
    def avg_score(self) -> float:
        """所有评估器的平均分。"""
        scores = [r.score for r in self.results if r.score is not None]
        return sum(scores) / len(scores) if scores else 0.0

    def to_eval_run_result(self) -> Any:
        """聚合为统一的 EvalRunResult（向后兼容）。"""
        # Lazy import to avoid circular dependency
        from .models import EvalRunResult, EvalRunStatus
        result = EvalRunResult(
            example_id=self.example_id,
            run_id=self.run_id or "",
            status=EvalRunStatus.COMPLETED if self.all_passed else EvalRunStatus.FAILED,
            metric_results=[
                MetricResult(
                    metric_name=r.evaluator_name,
                    score=r.score or (1.0 if r.passed else 0.0),
                    reasoning=r.message,
                    passed=r.passed,
                    details=r.details,
                )
                for r in self.results
            ],
            summary={
                "avg_score": self.avg_score,
                "all_passed": self.all_passed,
            },
            started_at=datetime.now(),
            finished_at=datetime.now(),
            errors=[] if not self.any_failed else ["One or more evaluators failed"],
        )
        return result

    def to_summary(self) -> dict[str, Any]:
        """输出到评估结果示例。"""
        from dataclasses import asdict
        return {
            "example_id": self.example_id,
            "run_id": self.run_id,
            "trace_id": self.trace_id,
            "all_passed": self.all_passed,
            "avg_score": self.avg_score,
            "results": [asdict(r) for r in self.results],
        }


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
    example_evaluations: list[ExampleEvaluation] = field(default_factory=list)
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
    """评估器协议 (7.1)。

    所有评估器（RAGAS、Agent Native、自定义）都应实现此协议。
    不强制 evaluate_batch — batch 属于 Runner。
    """

    @property
    def name(self) -> str:
        ...

    async def evaluate(
        self,
        context: EvaluationContext,
    ) -> EvaluationResult:
        """评估单个样本。"""
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


def eval_run_result_to_evaluation_result(
    eval_result: Any,
    run_id: str | None = None,
    example_id: str | None = None,
    expected_output: str | None = None,
) -> EvaluationResult:
    """将 EvalRunResult 转换为 EvaluationResult（向后兼容）。"""
    metric_results = getattr(eval_result, "metric_results", [])

    if metric_results:
        avg_score = sum(m.score for m in metric_results) / len(metric_results)
        all_passed = all(m.passed for m in metric_results if m.passed is not None)
    else:
        avg_score = 0.0
        all_passed = False

    # 优先使用 old result 的 overall_score，否则用 metric_results 平均
    overall_score = getattr(eval_result, "overall_score", None)
    if overall_score is not None and overall_score > 0:
        score = overall_score
    else:
        score = avg_score

    # 向后兼容：error_message
    error_msg = getattr(eval_result, "error_message", None) or getattr(eval_result, "error", None)

    # run_id: 优先用参数，其次用 old result（0 视为 None）
    effective_run_id = run_id
    if effective_run_id is None:
        old_run_id = getattr(eval_result, "run_id", None)
        effective_run_id = str(old_run_id) if old_run_id else None

    # example_id: 优先用参数，其次用 old result
    effective_example_id = example_id or str(getattr(eval_result, "case_id", ""))

    return EvaluationResult(
        evaluator_name="agent",
        run_id=effective_run_id,
        example_id=effective_example_id,
        passed=all_passed,
        score=score,
        label=None,
        message=str(error_msg) if error_msg else None,
        details={
            "agent_key": getattr(eval_result, "agent_key", None),
            "dataset_id": getattr(eval_result, "dataset_id", None),
        },
        metric_results=[
            MetricResult(
                metric_name=m.metric_name,
                score=m.score,
                reasoning=m.reasoning,
                passed=m.passed,
                details=getattr(m, "details", {}),
            )
            for m in metric_results
        ],
        duration_ms=getattr(eval_result, "duration_ms", 0),
    )


__all__ = [
    # Enums
    "RunStatus",
    "EvaluationRunStatus",
    "ExpectationType",
    "MetricScore",
    # Data
    "Expectation",
    "MetricResult",
    "DatasetExample",
    "SpanSummary",
    "EvaluationContext",
    "EvaluationResult",
    "ExampleEvaluation",
    "EvaluationRun",
    # Protocol
    "RunView",
    "Evaluator",
    # Adapter
    "eval_case_to_dataset_example",
    "eval_run_result_to_evaluation_result",
]
