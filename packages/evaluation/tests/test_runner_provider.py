"""EvaluationRunner + ProviderRegistry 集成测试。"""

from __future__ import annotations

import warnings
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from evaluation.contracts import EvalCase, EvalMetricResult, EvalRunConfig, EvalRunResult
from evaluation.runner import EvaluationRunner
from evaluation.providers.registry import ProviderRegistry


# ── 辅助 mock ────────────────────────────────────────────────────────


class _StubProvider:
    """可控的 EvalProvider mock。"""

    def __init__(self, name: str = "stub", score: float = 0.75):
        self.name = name
        self._score = score

    def get_metric(self, metric_name: str):
        raise NotImplementedError

    def list_metrics(self) -> list[str]:
        return ["faithfulness", "answer_relevancy"]

    async def evaluate(self, cases, metrics, config):
        metric_results = [
            EvalMetricResult(metric_name=m, score=self._score)
            for m in metrics
        ]
        return EvalRunResult(
            metric_results=metric_results,
            overall_score=self._score,
        )


@pytest.fixture
def sample_case():
    return EvalCase(
        id=1,
        input_text="测试问题",
        expected_output="测试回答",
        context=["测试上下文"],
    )


@pytest.fixture
def sample_config():
    return EvalRunConfig(
        name="test-run",
        metric_configs=[{"name": "faithfulness"}],
    )


# ── Provider 模式测试 ────────────────────────────────────────────────


class TestRunnerProviderMode:
    def test_use_provider_property(self):
        reg = ProviderRegistry()
        runner = EvaluationRunner(provider_registry=reg)
        assert runner.use_provider is True

        runner_legacy = EvaluationRunner(judge=MagicMock())
        assert runner_legacy.use_provider is False

    @pytest.mark.asyncio
    async def test_run_single_case_with_provider(self, sample_case, sample_config):
        reg = ProviderRegistry()
        provider = _StubProvider(score=0.88)
        reg.register(provider)

        runner = EvaluationRunner(provider_registry=reg)
        result = await runner.run_single_case(sample_case, sample_config)

        assert result.overall_score == 0.88
        assert result.error_message is None
        assert len(result.metric_results) > 0

    @pytest.mark.asyncio
    async def test_run_batch_with_provider(self, sample_config):
        cases = [
            EvalCase(id=1, input_text="Q1", expected_output="A1"),
            EvalCase(id=2, input_text="Q2", expected_output="A2"),
        ]
        reg = ProviderRegistry()
        reg.register(_StubProvider(score=0.9))

        runner = EvaluationRunner(provider_registry=reg)
        results = await runner.run_batch(cases, sample_config)

        assert len(results) >= 1
        assert results[0].overall_score == 0.9

    @pytest.mark.asyncio
    async def test_provider_error_returns_error_result(self, sample_case, sample_config):
        class _FailingProvider(_StubProvider):
            async def evaluate(self, cases, metrics, config):
                raise RuntimeError("Provider exploded")

        reg = ProviderRegistry()
        reg.register(_FailingProvider())

        runner = EvaluationRunner(provider_registry=reg)
        result = await runner.run_single_case(sample_case, sample_config)

        assert result.error_message is not None
        assert "Provider exploded" in result.error_message


# ── Legacy 模式测试（向后兼容） ───────────────────────────────────────


class TestRunnerLegacyMode:
    @pytest.mark.asyncio
    async def test_run_single_case_legacy(self, sample_case, sample_config):
        """Legacy 模式仍能正常工作。"""
        judge = AsyncMock()
        judge.score = AsyncMock(return_value=(0.8, "good"))

        runner = EvaluationRunner(judge=judge)
        assert runner.use_provider is False

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = await runner.run_single_case(sample_case, sample_config)

        assert result.error_message is None
        assert result.overall_score > 0

    @pytest.mark.asyncio
    async def test_run_batch_legacy(self, sample_config):
        judge = AsyncMock()
        judge.score = AsyncMock(return_value=(0.7, "ok"))

        cases = [
            EvalCase(id=1, input_text="Q1", expected_output="A1"),
            EvalCase(id=2, input_text="Q2", expected_output="A2"),
        ]

        runner = EvaluationRunner(judge=judge)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            results = await runner.run_batch(cases, sample_config)

        assert len(results) == 2


# ── Metric 名称解析测试 ──────────────────────────────────────────────


class TestResolveMetricNames:
    def test_from_config(self):
        config = EvalRunConfig(metric_configs=[{"name": "faithfulness"}, {"name": "context_precision"}])
        names = EvaluationRunner._resolve_metric_names(config)
        assert names == ["faithfulness", "context_precision"]

    def test_fallback_to_builtin(self):
        config = EvalRunConfig(metric_configs=[])
        names = EvaluationRunner._resolve_metric_names(config)
        assert "answer_relevance" in names
        assert "faithfulness" in names
        assert "context_relevance" in names
