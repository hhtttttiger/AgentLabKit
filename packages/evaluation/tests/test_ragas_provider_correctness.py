"""DF-05 regression: ragas provider correctness on the pinned 0.4.x API.

Covers:
- result access via ``result[metric]`` per-row lists (``.get()`` does not
  exist on ragas 0.4.3's EvaluationResult — the old code crashed every
  successful evaluation);
- NaN/Infinity never reach results: unavailable becomes score=None,
  passed=None, never 0.0 and never FAIL;
- judge model resolution is explicit: per-config key overrides the module
  default, and a missing judge model fails fast instead of falling back to
  a hardcoded vendor model.
"""
from __future__ import annotations

import math
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from evaluation.contracts import (
    EvalCase,
    EvalMetricResult,
    EvalRunConfig,
    EvalRunResult,
)
from evaluation.contracts_v2 import eval_run_result_to_evaluation_result
from evaluation.providers.ragas_provider import RAGASEvalProvider, _score_or_none

def _cases(n: int = 2) -> list[EvalCase]:
    return [
        EvalCase(id=i + 1, dataset_id=1, input_text=f"q{i}", expected_output=f"a{i}")
        for i in range(n)
    ]


class _FakeEvaluationResult:
    """Stand-in for ragas 0.4.3 EvaluationResult: __getitem__ -> list[float]."""

    def __init__(self, per_metric: dict[str, list[float]]) -> None:
        self._per_metric = per_metric

    def __getitem__(self, metric_name: str) -> list[float]:
        return self._per_metric[metric_name]


def _make_provider(**kwargs: Any) -> RAGASEvalProvider:
    # Direct llm injection skips gateway resolution in these tests.
    kwargs.setdefault("llm", MagicMock())
    return RAGASEvalProvider(**kwargs)


@pytest.mark.asyncio
async def test_result_access_uses_getitem_and_preserves_zero_scores():
    provider = _make_provider()
    fake = _FakeEvaluationResult({
        "faithfulness": [float("nan"), 0.0],
    })
    with patch("ragas.evaluate", return_value=fake):
        results = await provider.evaluate(
            _cases(2), ["faithfulness"], EvalRunConfig(),
        )

    assert len(results) == 2

    first, second = results
    # Row 0: NaN -> unavailable (score None, passed None, no FAIL verdict)
    assert first.metric_results[0].metric_name == "faithfulness"
    assert first.metric_results[0].score is None
    assert first.metric_results[0].passed is None
    assert first.overall_score is None, "no available score is not 0.0"

    # Row 1: a legitimate 0.0 survives exactly
    assert second.metric_results[0].score == 0.0
    assert second.overall_score == 0.0


@pytest.mark.asyncio
async def test_unavailable_rows_do_not_fail_the_whole_evaluation():
    provider = _make_provider()
    fake = _FakeEvaluationResult({
        "faithfulness": [0.5, float("nan")],
        "context_precision": [float("inf"), 1.0],
    })
    with patch("ragas.evaluate", return_value=fake):
        results = await provider.evaluate(
            _cases(2), ["faithfulness", "context_precision"], EvalRunConfig(),
        )

    assert all(r.error_message is None for r in results)
    first, second = results
    assert first.overall_score == 0.5, "only the available metric counts"
    assert second.overall_score == 1.0


@pytest.mark.asyncio
async def test_missing_judge_model_fails_fast_without_vendor_fallback():
    gateway = MagicMock()
    gateway.resolve_provider_config = AsyncMock()
    provider = RAGASEvalProvider(model_name="", gateway_service=gateway)

    results = await provider.evaluate(_cases(1), ["faithfulness"], EvalRunConfig())

    assert len(results) == 1
    assert results[0].error_message is not None
    assert "Judge model not configured" in results[0].error_message
    gateway.resolve_provider_config.assert_not_awaited()


@pytest.mark.asyncio
async def test_per_config_judge_model_overrides_module_default():
    gateway = MagicMock()
    resolved = MagicMock(provider="openai", api_key="k", base_url=None, model="cfg-model")
    gateway.resolve_provider_config = AsyncMock(return_value=resolved)
    provider = RAGASEvalProvider(model_name="module-default", gateway_service=gateway)
    fake = _FakeEvaluationResult({"faithfulness": [1.0]})

    config = EvalRunConfig(judge_model_key="per-config-judge")
    with patch("ragas.evaluate", return_value=fake):
        await provider.evaluate(_cases(1), ["faithfulness"], config)

    gateway.resolve_provider_config.assert_awaited_once_with("per-config-judge")


def test_score_or_none_sanitizer():
    assert _score_or_none(0.0) == 0.0
    assert _score_or_none("0.75") == 0.75
    assert _score_or_none(float("nan")) is None
    assert _score_or_none(float("inf")) is None
    assert _score_or_none(float("-inf")) is None
    assert _score_or_none(None) is None
    assert _score_or_none("not-a-number") is None


def test_v2_conversion_all_unavailable_scores_stay_none():
    legacy = EvalRunResult(
        case_id=7,
        metric_results=[
            EvalMetricResult(metric_name="faithfulness", score=None, passed=None),
            EvalMetricResult(metric_name="context_precision", score=None, passed=None),
        ],
        overall_score=None,
    )
    converted = eval_run_result_to_evaluation_result(legacy, example_id="7")
    assert converted.score is None
    assert converted.passed is None


def test_v2_conversion_zero_score_is_a_real_score():
    legacy = EvalRunResult(
        case_id=8,
        metric_results=[EvalMetricResult(metric_name="faithfulness", score=0.0, passed=False)],
        overall_score=0.0,
    )
    converted = eval_run_result_to_evaluation_result(legacy, example_id="8")
    assert converted.score == 0.0
    assert converted.passed is False


def test_summary_avg_skips_unavailable():
    # Mirrors run_service/application adapter summary logic: None never
    # enters the average, and an empty set of scores yields None, not 0.
    scores = [s for s in [0.5, None, 1.0] if s is not None]
    assert round(sum(scores) / len(scores), 4) == 0.75
    empty = [s for s in [None, None] if s is not None]
    avg = round(sum(empty) / len(empty), 4) if empty else None
    assert avg is None
    assert not (math.isnan(avg) if avg is not None else False)
