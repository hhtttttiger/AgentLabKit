"""EvaluationRunner 边界测试 — Phase 0 安全网。

覆盖：target_executor 调用、error handling、metric 结果聚合、空 metric 列表。
"""
from __future__ import annotations

import warnings
from unittest.mock import AsyncMock, MagicMock

import pytest

from evaluation.contracts import EvalCase, EvalMetricResult, EvalRunConfig, EvalRunResult
from evaluation.runner import EvaluationRunner
from evaluation.providers.registry import ProviderRegistry


# ── fixtures ────────────────────────────────────────────────────────


def _case(id: int = 1, **kwargs) -> EvalCase:
    defaults = dict(input_text="test input", expected_output="test output")
    defaults.update(kwargs)
    return EvalCase(id=id, **defaults)


def _config(**kwargs) -> EvalRunConfig:
    defaults = dict(name="test-run", metric_configs=[{"name": "faithfulness"}])
    defaults.update(kwargs)
    return EvalRunConfig(**defaults)


# ── target_executor 调用 ───────────────────────────────────────────


class TestTargetExecutor:
    @pytest.mark.asyncio
    async def test_executor_called_with_case_and_config(self) -> None:
        executor = AsyncMock()
        executor.execute = AsyncMock(return_value="executor output")

        judge = AsyncMock()
        judge.score = AsyncMock(return_value=(0.8, "good"))

        runner = EvaluationRunner(judge=judge)
        case = _case()
        config = _config()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await runner.run_single_case(case, config, target_executor=executor)

        executor.execute.assert_called_once_with(case, config)
        assert result.actual_output == "executor output"

    @pytest.mark.asyncio
    async def test_executor_error_returns_error_result(self) -> None:
        executor = AsyncMock()
        executor.execute = AsyncMock(side_effect=RuntimeError("executor failed"))

        runner = EvaluationRunner(judge=MagicMock())
        result = await runner.run_single_case(_case(), _config(), target_executor=executor)

        assert result.error_message is not None
        assert "executor failed" in result.error_message
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_no_executor_uses_expected_output_fallback(self) -> None:
        judge = AsyncMock()
        judge.score = AsyncMock(return_value=(0.9, "ok"))

        runner = EvaluationRunner(judge=judge)
        case = _case(expected_output="fallback text")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await runner.run_single_case(case, _config())

        assert result.actual_output == "fallback text"


# ── error handling ─────────────────────────────────────────────────


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_provider_batch_error_returns_single_error(self) -> None:
        class _FailingProvider:
            name = "fail"

            def get_metric(self, name):
                raise NotImplementedError

            def list_metrics(self):
                return []

            async def evaluate(self, cases, metrics, config):
                raise RuntimeError("batch explosion")

        reg = ProviderRegistry()
        reg.register(_FailingProvider())

        runner = EvaluationRunner(provider_registry=reg)
        results = await runner.run_batch(
            [_case(1), _case(2)],
            _config(),
        )

        assert len(results) == 1
        assert results[0].error_message is not None
        assert "batch explosion" in results[0].error_message

    @pytest.mark.asyncio
    async def test_provider_single_case_error(self) -> None:
        class _FailingProvider:
            name = "fail"

            def get_metric(self, name):
                raise NotImplementedError

            def list_metrics(self):
                return []

            async def evaluate(self, cases, metrics, config):
                raise RuntimeError("single explosion")

        reg = ProviderRegistry()
        reg.register(_FailingProvider())

        runner = EvaluationRunner(provider_registry=reg)
        result = await runner.run_single_case(_case(), _config())

        assert result.error_message is not None
        assert "single explosion" in result.error_message


# ── metric 结果聚合 ────────────────────────────────────────────────


class TestMetricAggregation:
    @pytest.mark.asyncio
    async def test_overall_score_is_average(self) -> None:
        """Legacy 模式下 overall_score 应该是各 metric 的平均值。"""

        class _ConstMetric:
            def __init__(self, name: str, score: float):
                self._name = name
                self._score = score

            async def evaluate(self, **kwargs):
                return EvalMetricResult(metric_name=self._name, score=self._score)

        judge = AsyncMock()
        runner = EvaluationRunner(judge=judge)

        # 两个独立 metric，分别返回 0.6 和 0.8
        fake_metrics = [_ConstMetric("m1", 0.6), _ConstMetric("m2", 0.8)]
        runner._resolve_legacy_metrics = lambda config: fake_metrics

        result = await runner.run_single_case(_case(), _config())

        # 0.6 和 0.8 的平均值
        assert result.overall_score == 0.7

    @pytest.mark.asyncio
    async def test_empty_metrics_returns_zero_score(self) -> None:
        judge = AsyncMock()
        runner = EvaluationRunner(judge=judge)

        # 空 metric 列表
        runner._resolve_legacy_metrics = lambda config: []

        result = await runner.run_single_case(_case(), _config())
        assert result.overall_score == 0.0


# ── metric name 解析 ───────────────────────────────────────────────


class TestMetricNameResolution:
    def test_empty_config_uses_all_builtin(self) -> None:
        config = EvalRunConfig(metric_configs=[])
        names = EvaluationRunner._resolve_metric_names(config)
        assert len(names) == 3
        assert "faithfulness" in names

    def test_custom_metric_not_in_map_passes_through(self) -> None:
        config = EvalRunConfig(metric_configs=[{"name": "custom_metric"}])
        names = EvaluationRunner._resolve_metric_names(config)
        assert names == ["custom_metric"]

    def test_mixed_mapped_and_unmapped(self) -> None:
        config = EvalRunConfig(metric_configs=[
            {"name": "answer_relevance"},
            {"name": "custom_metric"},
        ])
        names = EvaluationRunner._resolve_metric_names(config)
        assert names == ["answer_relevancy", "custom_metric"]
