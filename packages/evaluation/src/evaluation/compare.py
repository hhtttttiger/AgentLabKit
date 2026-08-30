"""EvaluationRun 比较器。

比较两个 EvaluationRun，识别改进、回归和未变化的案例。

核心原则：
- compare_runs 强类型接受 EvaluationRun（不再接受 Any）
- 比较前验证可比性（dataset_id 等）
- example_id 是对齐 baseline/candidate 的唯一 key
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .contracts_v2 import EvaluationRun


class IncompatibleEvaluationRuns(Exception):
    """两个 EvaluationRun 不可比较。"""

    def __init__(self, reasons: list[str]) -> None:
        self.reasons = reasons
        super().__init__(f"Incompatible evaluation runs: {'; '.join(reasons)}")


class ChangeType(str, Enum):
    IMPROVED = "improved"
    REGRESSED = "regressed"
    UNCHANGED = "unchanged"
    NEW = "new"           # 只在新 run 中存在
    REMOVED = "removed"   # 只在旧 run 中存在


@dataclass(frozen=True, slots=True)
class ExampleDiff:
    """单个样本的比较结果。"""
    example_id: str
    change_type: ChangeType
    baseline_score: float | None = None
    current_score: float | None = None
    score_delta: float | None = None
    baseline_error: str | None = None
    current_error: str | None = None


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    """两个 EvaluationRun 的比较结果。"""
    baseline_run_id: str
    current_run_id: str
    improved: list[ExampleDiff] = field(default_factory=list)
    regressed: list[ExampleDiff] = field(default_factory=list)
    unchanged: list[ExampleDiff] = field(default_factory=list)
    new_examples: list[ExampleDiff] = field(default_factory=list)
    removed_examples: list[ExampleDiff] = field(default_factory=list)

    @property
    def total_changes(self) -> int:
        return len(self.improved) + len(self.regressed) + len(self.new_examples) + len(self.removed_examples)

    @property
    def regression_count(self) -> int:
        return len(self.regressed)

    @property
    def improvement_count(self) -> int:
        return len(self.improved)

    @property
    def summary(self) -> dict[str, int]:
        return {
            "improved": len(self.improved),
            "regressed": len(self.regressed),
            "unchanged": len(self.unchanged),
            "new": len(self.new_examples),
            "removed": len(self.removed_examples),
        }


def compare_runs(
    baseline: EvaluationRun,
    current: EvaluationRun,
    score_threshold: float = 0.01,
) -> ComparisonResult:
    """比较两个 EvaluationRun。

    Args:
        baseline: 基线评估运行
        current: 当前评估运行
        score_threshold: 分数变化阈值，低于此值视为 unchanged

    Returns:
        ComparisonResult 包含改进、回归和未变化的案例

    Raises:
        IncompatibleEvaluationRuns: 当两个 run 不可比较时
    """
    # ── Comparability validation ───────────────────────────────────
    _validate_comparable(baseline, current)

    # 构建 baseline 的 example_id → result 映射
    baseline_results = {}
    for result in baseline.results:
        baseline_results[result.example_id] = result

    # 构建 current 的 example_id → result 映射
    current_results = {}
    for result in current.results:
        current_results[result.example_id] = result

    improved = []
    regressed = []
    unchanged = []
    new_examples = []
    removed_examples = []

    # 检查 current 中的每个 example
    for example_id, current_result in current_results.items():
        baseline_result = baseline_results.get(example_id)

        if baseline_result is None:
            # 新增的 example
            new_examples.append(ExampleDiff(
                example_id=example_id,
                change_type=ChangeType.NEW,
                current_score=current_result.overall_score,
                current_error=current_result.error_message,
            ))
            continue

        # 比较分数
        baseline_score = baseline_result.overall_score
        current_score = current_result.overall_score

        # 处理错误情况
        if baseline_result.error_message and current_result.error_message:
            # 两者都有错误，视为 unchanged
            unchanged.append(ExampleDiff(
                example_id=example_id,
                change_type=ChangeType.UNCHANGED,
                baseline_score=baseline_score,
                current_score=current_score,
                baseline_error=baseline_result.error_message,
                current_error=current_result.error_message,
            ))
        elif baseline_result.error_message:
            # 从错误恢复，视为 improved
            improved.append(ExampleDiff(
                example_id=example_id,
                change_type=ChangeType.IMPROVED,
                baseline_score=baseline_score,
                current_score=current_score,
                score_delta=current_score - baseline_score,
                baseline_error=baseline_result.error_message,
            ))
        elif current_result.error_message:
            # 新出现错误，视为 regressed
            regressed.append(ExampleDiff(
                example_id=example_id,
                change_type=ChangeType.REGRESSED,
                baseline_score=baseline_score,
                current_score=current_score,
                score_delta=current_score - baseline_score,
                current_error=current_result.error_message,
            ))
        else:
            # 正常比较
            delta = current_score - baseline_score
            if abs(delta) < score_threshold:
                unchanged.append(ExampleDiff(
                    example_id=example_id,
                    change_type=ChangeType.UNCHANGED,
                    baseline_score=baseline_score,
                    current_score=current_score,
                    score_delta=delta,
                ))
            elif delta > 0:
                improved.append(ExampleDiff(
                    example_id=example_id,
                    change_type=ChangeType.IMPROVED,
                    baseline_score=baseline_score,
                    current_score=current_score,
                    score_delta=delta,
                ))
            else:
                regressed.append(ExampleDiff(
                    example_id=example_id,
                    change_type=ChangeType.REGRESSED,
                    baseline_score=baseline_score,
                    current_score=current_score,
                    score_delta=delta,
                ))

    # 检查 baseline 中存在但 current 中不存在的 example
    for example_id, baseline_result in baseline_results.items():
        if example_id not in current_results:
            removed_examples.append(ExampleDiff(
                example_id=example_id,
                change_type=ChangeType.REMOVED,
                baseline_score=baseline_result.overall_score,
                baseline_error=baseline_result.error_message,
            ))

    return ComparisonResult(
        baseline_run_id=baseline.run_id,
        current_run_id=current.run_id,
        improved=improved,
        regressed=regressed,
        unchanged=unchanged,
        new_examples=new_examples,
        removed_examples=removed_examples,
    )


def format_comparison_report(result: ComparisonResult) -> str:
    """格式化比较结果为可读报告。"""
    lines = [
        f"Comparison: {result.baseline_run_id} vs {result.current_run_id}",
        f"=" * 60,
        f"Summary: {result.summary}",
        "",
    ]

    if result.improved:
        lines.append(f"✅ Improved ({len(result.improved)}):")
        for diff in result.improved:
            delta = f"+{diff.score_delta:.3f}" if diff.score_delta else ""
            lines.append(f"  - {diff.example_id}: {diff.baseline_score:.3f} → {diff.current_score:.3f} ({delta})")

    if result.regressed:
        lines.append(f"❌ Regressed ({len(result.regressed)}):")
        for diff in result.regressed:
            delta = f"{diff.score_delta:.3f}" if diff.score_delta else ""
            lines.append(f"  - {diff.example_id}: {diff.baseline_score:.3f} → {diff.current_score:.3f} ({delta})")
            if diff.current_error:
                lines.append(f"    Error: {diff.current_error}")

    if result.unchanged:
        lines.append(f"➖ Unchanged ({len(result.unchanged)}):")
        for diff in result.unchanged[:5]:  # 只显示前5个
            lines.append(f"  - {diff.example_id}: {diff.current_score:.3f}")
        if len(result.unchanged) > 5:
            lines.append(f"  ... and {len(result.unchanged) - 5} more")

    if result.new_examples:
        lines.append(f"🆕 New ({len(result.new_examples)}):")
        for diff in result.new_examples:
            lines.append(f"  - {diff.example_id}: {diff.current_score:.3f}")

    if result.removed_examples:
        lines.append(f"🗑️ Removed ({len(result.removed_examples)}):")
        for diff in result.removed_examples:
            lines.append(f"  - {diff.example_id}")

    return "\n".join(lines)


def _validate_comparable(baseline: EvaluationRun, current: EvaluationRun) -> None:
    """验证两个 EvaluationRun 是否可比较。

    检查：
    - dataset_id 必须一致
    - dataset_version 在两者都设置时必须一致
    - evaluator_specs 在两者都设置时检查一致性

    Raises:
        IncompatibleEvaluationRuns: 当不可比较时
    """
    reasons: list[str] = []

    # dataset_id 必须一致
    if baseline.dataset_id != current.dataset_id:
        reasons.append(
            f"dataset_id mismatch: baseline={baseline.dataset_id!r}, "
            f"current={current.dataset_id!r}"
        )

    # dataset_version: 当两者都设置时检查一致性
    if (baseline.dataset_version is not None
            and current.dataset_version is not None
            and baseline.dataset_version != current.dataset_version):
        reasons.append(
            f"dataset_version mismatch: baseline={baseline.dataset_version!r}, "
            f"current={current.dataset_version!r}"
        )

    # evaluator_specs: 当两者都设置时检查一致性
    if baseline.evaluator_specs and current.evaluator_specs:
        baseline_specs = {(s.name, s.version) for s in baseline.evaluator_specs}
        current_specs = {(s.name, s.version) for s in current.evaluator_specs}
        if baseline_specs != current_specs:
            reasons.append(
                f"evaluator_specs mismatch: "
                f"baseline={[f'{s.name}@{s.version}' for s in baseline.evaluator_specs]!r}, "
                f"current={[f'{s.name}@{s.version}' for s in current.evaluator_specs]!r}"
            )

    if reasons:
        raise IncompatibleEvaluationRuns(reasons)


__all__ = [
    "ChangeType",
    "ExampleDiff",
    "ComparisonResult",
    "IncompatibleEvaluationRuns",
    "compare_runs",
    "format_comparison_report",
]
