"""Tests for EvaluationRun comparison."""

from __future__ import annotations

import pytest

from evaluation.compare import (
    ChangeType,
    ComparisonResult,
    ExampleDiff,
    IncompatibleEvaluationRuns,
    compare_runs,
    format_comparison_report,
)
from evaluation.contracts_v2 import (
    EvaluationResult,
    EvaluationRun,
    EvaluationRunStatus,
    MetricResult,
)


def _make_run(run_id: str, results: list[EvaluationResult]) -> EvaluationRun:
    return EvaluationRun(
        run_id=run_id,
        dataset_id="dataset-1",
        agent_key="chat",
        status=EvaluationRunStatus.COMPLETED,
        results=results,
        total_examples=len(results),
        completed_examples=len([r for r in results if r.error_message is None]),
        failed_examples=len([r for r in results if r.error_message is not None]),
    )


def _make_result(example_id: str, score: float, error: str | None = None) -> EvaluationResult:
    return EvaluationResult(
        example_id=example_id,
        score=score,
        message=error,
        metric_results=[MetricResult(metric_name="test", score=score)],
    )


# ── compare_runs ───────────────────────────────────────────────────


class TestCompareRuns:
    def test_improved_examples(self):
        baseline = _make_run("baseline", [
            _make_result("1", 0.5),
            _make_result("2", 0.6),
        ])
        current = _make_run("current", [
            _make_result("1", 0.8),
            _make_result("2", 0.9),
        ])

        result = compare_runs(baseline, current)

        assert len(result.improved) == 2
        assert result.improvement_count == 2
        assert result.regression_count == 0
        assert result.improved[0].example_id == "1"
        assert result.improved[0].score_delta == pytest.approx(0.3)

    def test_regressed_examples(self):
        baseline = _make_run("baseline", [
            _make_result("1", 0.8),
            _make_result("2", 0.9),
        ])
        current = _make_run("current", [
            _make_result("1", 0.5),
            _make_result("2", 0.6),
        ])

        result = compare_runs(baseline, current)

        assert len(result.regressed) == 2
        assert result.regression_count == 2
        assert result.improvement_count == 0
        assert result.regressed[0].score_delta == pytest.approx(-0.3)

    def test_unchanged_examples(self):
        baseline = _make_run("baseline", [
            _make_result("1", 0.8),
            _make_result("2", 0.9),
        ])
        current = _make_run("current", [
            _make_result("1", 0.8),
            _make_result("2", 0.9),
        ])

        result = compare_runs(baseline, current)

        assert len(result.unchanged) == 2
        assert result.improvement_count == 0
        assert result.regression_count == 0

    def test_unchanged_within_threshold(self):
        baseline = _make_run("baseline", [
            _make_result("1", 0.800),
        ])
        current = _make_run("current", [
            _make_result("1", 0.805),
        ])

        # 默认阈值 0.01
        result = compare_runs(baseline, current)
        assert len(result.unchanged) == 1

    def test_new_examples(self):
        baseline = _make_run("baseline", [
            _make_result("1", 0.8),
        ])
        current = _make_run("current", [
            _make_result("1", 0.8),
            _make_result("2", 0.9),
        ])

        result = compare_runs(baseline, current)

        assert len(result.new_examples) == 1
        assert result.new_examples[0].example_id == "2"
        assert result.new_examples[0].change_type == ChangeType.NEW

    def test_removed_examples(self):
        baseline = _make_run("baseline", [
            _make_result("1", 0.8),
            _make_result("2", 0.9),
        ])
        current = _make_run("current", [
            _make_result("1", 0.8),
        ])

        result = compare_runs(baseline, current)

        assert len(result.removed_examples) == 1
        assert result.removed_examples[0].example_id == "2"
        assert result.removed_examples[0].change_type == ChangeType.REMOVED

    def test_mixed_changes(self):
        baseline = _make_run("baseline", [
            _make_result("1", 0.5),   # improved
            _make_result("2", 0.9),   # regressed
            _make_result("3", 0.8),   # unchanged
        ])
        current = _make_run("current", [
            _make_result("1", 0.8),   # improved
            _make_result("2", 0.6),   # regressed
            _make_result("3", 0.8),   # unchanged
            _make_result("4", 0.7),   # new
        ])

        result = compare_runs(baseline, current)

        assert len(result.improved) == 1
        assert len(result.regressed) == 1
        assert len(result.unchanged) == 1
        assert len(result.new_examples) == 1
        assert result.total_changes == 3  # improved + regressed + new

    def test_error_recovery(self):
        baseline = _make_run("baseline", [
            _make_result("1", 0.0, error="timeout"),
        ])
        current = _make_run("current", [
            _make_result("1", 0.8),
        ])

        result = compare_runs(baseline, current)

        assert len(result.improved) == 1
        assert result.improved[0].baseline_error == "timeout"

    def test_error_introduction(self):
        baseline = _make_run("baseline", [
            _make_result("1", 0.8),
        ])
        current = _make_run("current", [
            _make_result("1", 0.0, error="timeout"),
        ])

        result = compare_runs(baseline, current)

        assert len(result.regressed) == 1
        assert result.regressed[0].current_error == "timeout"

    def test_both_have_errors(self):
        baseline = _make_run("baseline", [
            _make_result("1", 0.0, error="error1"),
        ])
        current = _make_run("current", [
            _make_result("1", 0.0, error="error2"),
        ])

        result = compare_runs(baseline, current)

        assert len(result.unchanged) == 1

    def test_custom_threshold(self):
        baseline = _make_run("baseline", [
            _make_result("1", 0.800),
        ])
        current = _make_run("current", [
            _make_result("1", 0.805),
        ])

        # 使用更小的阈值
        result = compare_runs(baseline, current, score_threshold=0.001)
        assert len(result.improved) == 1

    def test_empty_runs(self):
        baseline = _make_run("baseline", [])
        current = _make_run("current", [])

        result = compare_runs(baseline, current)

        assert result.total_changes == 0
        assert len(result.improved) == 0
        assert len(result.regressed) == 0


# ── ComparisonResult ───────────────────────────────────────────────


class TestComparisonResult:
    def test_summary(self):
        result = ComparisonResult(
            baseline_run_id="baseline",
            current_run_id="current",
            improved=[ExampleDiff("1", ChangeType.IMPROVED)],
            regressed=[ExampleDiff("2", ChangeType.REGRESSED)],
            unchanged=[ExampleDiff("3", ChangeType.UNCHANGED)],
            new_examples=[ExampleDiff("4", ChangeType.NEW)],
        )

        summary = result.summary
        assert summary["improved"] == 1
        assert summary["regressed"] == 1
        assert summary["unchanged"] == 1
        assert summary["new"] == 1
        assert summary["removed"] == 0

    def test_total_changes(self):
        result = ComparisonResult(
            baseline_run_id="baseline",
            current_run_id="current",
            improved=[ExampleDiff("1", ChangeType.IMPROVED)],
            regressed=[ExampleDiff("2", ChangeType.REGRESSED)],
        )

        assert result.total_changes == 2


# ── format_comparison_report ───────────────────────────────────────


class TestFormatReport:
    def test_basic_report(self):
        result = ComparisonResult(
            baseline_run_id="baseline",
            current_run_id="current",
            improved=[
                ExampleDiff("1", ChangeType.IMPROVED, 0.5, 0.8, 0.3),
            ],
            regressed=[
                ExampleDiff("2", ChangeType.REGRESSED, 0.9, 0.6, -0.3),
            ],
            unchanged=[
                ExampleDiff("3", ChangeType.UNCHANGED, 0.8, 0.8, 0.0),
            ],
        )

        report = format_comparison_report(result)

        assert "baseline" in report
        assert "current" in report
        assert "Improved (1)" in report
        assert "Regressed (1)" in report
        assert "Unchanged (1)" in report

    def test_report_with_errors(self):
        result = ComparisonResult(
            baseline_run_id="baseline",
            current_run_id="current",
            regressed=[
                ExampleDiff("1", ChangeType.REGRESSED, 0.8, 0.0, -0.8, current_error="timeout"),
            ],
        )

        report = format_comparison_report(result)
        assert "timeout" in report

    def test_report_with_new_and_removed(self):
        result = ComparisonResult(
            baseline_run_id="baseline",
            current_run_id="current",
            new_examples=[
                ExampleDiff("1", ChangeType.NEW, current_score=0.8),
            ],
            removed_examples=[
                ExampleDiff("2", ChangeType.REMOVED, baseline_score=0.9),
            ],
        )

        report = format_comparison_report(result)
        assert "New (1)" in report
        assert "Removed (1)" in report


# ── ExampleDiff ────────────────────────────────────────────────────


class TestExampleDiff:
    def test_change_type_enum(self):
        assert ChangeType.IMPROVED == "improved"
        assert ChangeType.REGRESSED == "regressed"
        assert ChangeType.UNCHANGED == "unchanged"
        assert ChangeType.NEW == "new"
        assert ChangeType.REMOVED == "removed"


# ── Comparability Validation ───────────────────────────────────────


class TestComparabilityValidation:
    def test_different_dataset_id_raises(self):
        """dataset_id 不一致时抛出 IncompatibleEvaluationRuns。"""
        baseline = _make_run("baseline", [
            _make_result("1", 0.5),
        ])
        # 修改 dataset_id
        current = EvaluationRun(
            run_id="current",
            dataset_id="different-dataset",
            agent_key="chat",
            status=EvaluationRunStatus.COMPLETED,
            results=[_make_result("1", 0.8)],
            total_examples=1,
            completed_examples=1,
        )

        with pytest.raises(IncompatibleEvaluationRuns) as exc_info:
            compare_runs(baseline, current)

        assert "dataset_id" in str(exc_info.value)

    def test_same_dataset_id_passes(self):
        """dataset_id 一致时正常比较。"""
        baseline = _make_run("baseline", [_make_result("1", 0.5)])
        current = _make_run("current", [_make_result("1", 0.8)])

        result = compare_runs(baseline, current)
        assert len(result.improved) == 1

    @pytest.mark.asyncio
    async def test_replay_compare_uses_same_example_id(self):
        """Replay 比较时 baseline/candidate 使用同一个 example_id。

        这是验收测试 I 的核心：Example #42 baseline Run A 和 candidate Run B
        必须使用同一个 example_id，compare 不会把它们识别成 removed/new。
        """
        from evaluation.replay import (
            InMemoryRunStore,
            MockRunExecutor,
            ReplayConfig,
            ReplayRunner,
        )
        from evaluation.contracts_v2 import AgentRunSummary

        # 创建一个评估器，检查 example_id 一致性
        captured_ids: list[str] = []

        class ExampleIdCapturingEvaluator:
            name = "capturing"

            async def evaluate(self, context):
                captured_ids.append(context.example.example_id)
                return EvaluationResult(
                    example_id=context.example.example_id,
                    score=0.8,
                )

        store = InMemoryRunStore()
        original = AgentRunSummary(
            run_id="run-A",
            trace_id="trace-1",
            agent_key="refund-agent",
            input_text="refund order 123",
            output_text="refunded",
            status="completed",
        )
        await store.save_run(original)

        executor = MockRunExecutor(
            output_text="refunded v2",
            run_id="run-B",
            trace_id="trace-B",
        )
        evaluator = ExampleIdCapturingEvaluator()
        runner = ReplayRunner(store, executor, evaluator)

        result = await runner.replay(
            "run-A",
            ReplayConfig(example_id="refund-case-42"),
        )

        # 比较成功（没有 removed/new）
        assert result.comparison is not None
        assert len(result.comparison.removed_examples) == 0
        assert len(result.comparison.new_examples) == 0

        # baseline 和 candidate 使用同一个 example_id
        assert len(captured_ids) == 2
        assert captured_ids[0] == captured_ids[1] == "refund-case-42"
        assert original.run_id != executor.run_id
