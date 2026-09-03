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
class RunTargetView(Protocol):
    """Minimal target contract exposed to evaluation and replay consumers."""

    type: str
    agent_key: str | None
    agent_version: str | None
    workflow_id: str | None
    workflow_version: str | None


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
    def started_at(self) -> datetime | None: ...

    @property
    def finished_at(self) -> datetime | None: ...

    @property
    def target(self) -> RunTargetView | None: ...

    # Agent-native evaluators need these (tool/latency/cost evaluators)
    @property
    def tool_names(self) -> list[str]: ...

    @property
    def tool_call_count(self) -> int: ...

    @property
    def duration_ms(self) -> int | None: ...

    @property
    def total_input_tokens(self) -> int: ...

    @property
    def total_output_tokens(self) -> int: ...


# ── AgentRunSummary (concrete RunView implementation) ───────────────


@dataclass(frozen=True, slots=True)
class AgentRunSummary:
    """AgentRun 的摘要，用于评估上下文。

    实现 RunView 协议。保留向后兼容。

    ``started_at`` / ``finished_at``: 真实时间戳，来自 Runtime。
    历史数据如果没有这些字段，使用 None（禁止 datetime.now() 补假数据）。
    """
    run_id: str
    trace_id: str = ""
    agent_key: str = ""
    input_text: str = ""
    output_text: str = ""
    status: RunStatus = RunStatus.COMPLETED
    duration_ms: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    tool_call_count: int = 0
    tool_names: list[str] = field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    target: Any | None = None

    def __post_init__(self) -> None:
        # Coerce string status to RunStatus enum for backward compat
        if isinstance(self.status, str):
            object.__setattr__(self, 'status', RunStatus(self.status))

    # RunView protocol properties
    @property
    def input(self) -> str:
        return self.input_text

    @property
    def output(self) -> str | None:
        return self.output_text


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

    # P1: skip reason — 评估跳过时的说明（如无 trace、无 run）
    skip_reason: str | None = None

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
        """所有评估器都通过；没有任何 verdict 时不是 PASS。"""
        return self.passed is True

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
        """聚合为统一的 EvalRunResult（向后兼容）。

        注意：EvalRunResult 是旧版契约，字段映射有限。
        started_at/finished_at 在 EvalRunResult 中不存在，不伪造。
        """
        # Lazy import to avoid circular dependency
        from .contracts import EvalRunResult
        result = EvalRunResult(
            run_id=0,
            case_id=int(self.example_id) if self.example_id.isdigit() else 0,
            metric_results=[
                MetricResult(
                    metric_name=r.evaluator_name,
                    score=(
                        r.score
                        if r.score is not None
                        else (1.0 if r.passed is True else 0.0)
                    ),
                    reasoning=r.message,
                    passed=r.passed,
                    details=r.details,
                )
                for r in self.results
            ],
            overall_score=self.avg_score,
            error_message=None if not self.any_failed else "One or more evaluators failed",
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
class EvaluatorSpec:
    """描述一次评估运行使用的评估器。"""
    name: str
    version: str | None = None


@dataclass(init=False)
class EvaluationRun:
    """一次完整的评估运行。

    Canonical model: ``example_evaluations`` is the source of truth.
    ``results`` is a backward-compat read-only property derived from
    ``example_evaluations`` — no separate mutable list.

    Legacy callers can still pass ``results=[...]`` to the constructor;
    it seeds ``example_evaluations`` automatically.
    """
    run_id: str
    dataset_id: str
    agent_key: str
    status: EvaluationRunStatus
    example_evaluations: list[ExampleEvaluation]
    total_examples: int
    completed_examples: int
    failed_examples: int
    overall_score: float
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    dataset_version: str | None
    evaluator_specs: list[EvaluatorSpec]

    def __init__(
        self,
        run_id: str,
        dataset_id: str,
        agent_key: str,
        *,
        status: EvaluationRunStatus = EvaluationRunStatus.PENDING,
        results: list[EvaluationResult] | None = None,
        example_evaluations: list[ExampleEvaluation] | None = None,
        total_examples: int = 0,
        completed_examples: int = 0,
        failed_examples: int = 0,
        overall_score: float = 0.0,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        error_message: str | None = None,
        dataset_version: str | None = None,
        evaluator_specs: list[EvaluatorSpec] | None = None,
    ) -> None:
        self.run_id = run_id
        self.dataset_id = dataset_id
        self.agent_key = agent_key
        self.status = status
        self.total_examples = total_examples
        self.completed_examples = completed_examples
        self.failed_examples = failed_examples
        self.overall_score = overall_score
        self.started_at = started_at
        self.completed_at = completed_at
        self.error_message = error_message
        self.dataset_version = dataset_version
        self.evaluator_specs = evaluator_specs or []

        # Canonical: seed example_evaluations from results if only results given
        if results and not example_evaluations:
            eval_map: dict[str, list[EvaluationResult]] = {}
            for r in results:
                eval_map.setdefault(r.example_id, []).append(r)
            self.example_evaluations = [
                ExampleEvaluation(example_id=eid, results=eresults)
                for eid, eresults in eval_map.items()
            ]
        else:
            self.example_evaluations = example_evaluations or []

    @property
    def results(self) -> list[EvaluationResult]:
        """Backward-compat flat list — derived from example_evaluations."""
        return [
            result
            for example in self.example_evaluations
            for result in example.results
        ]


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


# ── TraceProvider (P1: trace data injection) ─────────────────────


@runtime_checkable
class TraceProvider(Protocol):
    """Trace 数据提供者 — DatasetEvaluationRunner 通过此协议获取 span 数据。

    实现可以是 TraceStore、ObservabilityClient 等。
    返回 None 表示 trace 不存在（run 可能太新或已过期）。
    """

    async def get_spans(self, trace_id: str) -> list[SpanSummary] | None:
        """获取指定 trace 的 span 列表。"""
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
        verdicts = [m.passed for m in metric_results if m.passed is not None]
        # No verdict is not a successful verdict.  Preserve the v2
        # tri-state meaning of passed (True / False / None).
        all_passed = all(verdicts) if verdicts else None
    else:
        avg_score = 0.0
        all_passed = None

    # ``0.0`` is a valid authoritative score; only a missing attribute falls
    # back to the metric average.  This matters for a legitimate all-failed
    # evaluation as well as for explicit zero scores.
    _missing = object()
    overall_score = getattr(eval_result, "overall_score", _missing)
    score = avg_score if overall_score is _missing or overall_score is None else overall_score

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
    "RunTargetView",
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
    "EvaluatorSpec",
    "EvaluationRun",
    # Protocol
    "RunView",
    "Evaluator",
    "TraceProvider",
    # Adapter
    "eval_case_to_dataset_example",
    "eval_run_result_to_evaluation_result",
]
