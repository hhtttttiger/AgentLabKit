"""RagasAdapter — canonical evidence → provider input 的映射与 gating 测试。

核心保证：
- 提供 evidence 时，retrieved_contexts 只来自 candidate evidence；
  DatasetExample.context（数据集 expectation）永远不会被当作 candidate 检索证据。
- 缺少 metric 声明需要的 evidence → score=None / passed=None + machine-readable
  reason；answer-only metric 不受影响。
- zero results 是合法输入（AVAILABLE），不会被预先当成 unavailable。
"""

from __future__ import annotations

from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from evaluation.contracts import EvalCase, EvalRunConfig
from evaluation.evidence import (
    EvidenceAvailability,
    EvaluationEvidence,
    RetrievalAttempt,
    RetrievalContextRef,
    RetrievalEvidence,
)
from evaluation.providers.ragas_provider import RAGASEvalProvider


def _make_ragas_module(evaluate_fn=None, dataset_cls=None, captured_items=None):
    """构建 mock ragas 模块，并捕获传入 from_list 的 items。"""
    mod = ModuleType("ragas")
    mod.evaluate = evaluate_fn or _fake_evaluate
    mod.EvaluationDataset = dataset_cls or _capturing_dataset_cls(captured_items or [])
    metrics_mod = ModuleType("ragas.metrics")
    metrics_mod.Faithfulness = MagicMock(return_value=MagicMock())
    metrics_mod.AnswerRelevancy = MagicMock(return_value=MagicMock())
    metrics_mod.ContextPrecision = MagicMock(return_value=MagicMock())
    mod.metrics = metrics_mod
    return mod


def _capturing_dataset_cls(captured):
    class _Dataset:
        def __init__(self, items):
            pass

        @classmethod
        def from_list(cls, items):
            captured.extend(items)
            return cls(items)

    return _Dataset


def _fake_evaluate(*args, dataset=None, metrics=None, llm=None, **kwargs):
    """每个 metric 每行返回一个可用分数（0.5）。"""
    result = {}
    for metric in metrics or []:
        name = getattr(metric, "name", None) or str(metric)
        result[name] = MagicMock()
        result[name].__getitem__ = lambda _, dataset=dataset: None
    return _RowResult({m.name if hasattr(m, "name") else str(m): [0.5] for m in (metrics or [])})


class _RowResult:
    def __init__(self, scores):
        self._scores = scores

    def __getitem__(self, metric_name):
        return self._scores[metric_name]


def _result_with(scores_by_metric):
    return _RowResult(scores_by_metric)


def _evidence(
    availability=EvidenceAvailability.AVAILABLE,
    attempts=None,
    reason=None,
):
    return EvaluationEvidence(
        example_id="example-1",
        run_id="candidate-run-id",
        trace_id="candidate-trace-id",
        input_text="q",
        actual_output="candidate answer",
        expected_output="reference answer",
        retrieval=RetrievalEvidence(
            availability=availability, attempts=tuple(attempts or ()), reason=reason,
        ),
    )


def _success_attempt(refs=("candidate-context-1",)):
    return RetrievalAttempt(
        succeeded=True,
        query="q",
        result_count=len(refs),
        refs=tuple(
            RetrievalContextRef(content_preview=ref, document_id=ref) for ref in refs
        ),
    )


def _failed_attempt(error="timeout"):
    return RetrievalAttempt(
        succeeded=False, query="q", result_count=0, error_message=error,
    )


@pytest.fixture
def captured_items():
    return []


def run_config_fixture():
    return EvalRunConfig(
        name="test",
        metric_configs=[{"name": name} for name in (
            "faithfulness", "answer_relevancy", "context_precision",
        )],
    )


def _evaluate_sync(provider, cases, metrics, config, evidence=None, scores=None):
    """带 mock ragas 的同步 evaluate，返回 (results, captured_items)。"""
    import asyncio

    captured = []
    ragas_mod = _make_ragas_module(
        evaluate_fn=lambda *a, **k: _result_with(scores or {
            "faithfulness": [0.8], "answer_relevancy": [0.7], "context_precision": [0.6],
        }),
        dataset_cls=_capturing_dataset_cls(captured),
    )
    with patch.dict("sys.modules", {"ragas": ragas_mod, "ragas.metrics": ragas_mod.metrics}):
        results = asyncio.run(provider.evaluate(cases, metrics, config, evidence=evidence))
    return results, captured


# ── Candidate evidence feeds the metric ──────────────────────────────


def test_metric_receives_candidate_contexts_not_dataset_context(captured_items):
    provider = RAGASEvalProvider(llm=MagicMock())
    case = EvalCase(
        id=1, input_text="q", expected_output="reference answer",
        context=["ALPHA-dataset-expectation"],
    )
    ev = _evidence(attempts=[_success_attempt(("BETA-candidate-context",))])
    results, items = _evaluate_sync(provider, [case], ["faithfulness"], run_config_fixture(), evidence=[ev])
    assert results[0].metric_results[0].score == 0.8
    assert items[0]["retrieved_contexts"] == ["BETA-candidate-context"]


def test_legacy_mode_without_evidence_gates_retrieval_metrics(captured_items):
    """Backward compatibility means 'old callers can still evaluate', NOT
    'DatasetExample.context silently becomes candidate retrieved_contexts'."""
    provider = RAGASEvalProvider(llm=MagicMock())
    case = EvalCase(
        id=1, input_text="q", expected_output="ref",
        context=["dataset-context"],
    )
    results, items = _evaluate_sync(
        provider, [case], ["faithfulness", "answer_relevancy"], run_config_fixture(),
    )
    by_name = {m.metric_name: m for m in results[0].metric_results}
    # Retrieval-aware metric: truthfully unavailable, never dataset context.
    assert by_name["faithfulness"].score is None
    assert by_name["faithfulness"].passed is None
    assert by_name["faithfulness"].reason == "evidence_not_provided"
    # Answer-only metric keeps working.
    assert by_name["answer_relevancy"].score == 0.7
    # faithfulness is never submitted with invented inputs.
    assert len(items) == 1
    assert items[0]["retrieved_contexts"] == []


# ── Missing evidence → truthful unavailable, per metric ─────────────


def test_unavailable_trace_gates_retrieval_metrics_only():
    provider = RAGASEvalProvider(llm=MagicMock())
    case = EvalCase(id=1, input_text="q", expected_output="ref")
    ev = _evidence(availability=EvidenceAvailability.UNAVAILABLE, reason="trace_unavailable")
    results, items = _evaluate_sync(
        provider, [case],
        ["faithfulness", "answer_relevancy", "context_precision"],
        run_config_fixture(), evidence=[ev],
    )
    by_name = {m.metric_name: m for m in results[0].metric_results}
    assert by_name["faithfulness"].score is None
    assert by_name["faithfulness"].passed is None
    assert by_name["faithfulness"].reason == "trace_unavailable"
    assert by_name["context_precision"].reason == "trace_unavailable"
    # Answer-only metric still computes.
    assert by_name["answer_relevancy"].score == 0.7
    # Only the answer-only metric reaches ragas; gated retrieval metrics are
    # never submitted with invented inputs.
    assert len(items) == 1
    assert items[0]["user_input"] == "q"


def test_no_retrieval_is_not_applicable_reason():
    provider = RAGASEvalProvider(llm=MagicMock())
    case = EvalCase(id=1, input_text="q", expected_output="ref")
    ev = _evidence(availability=EvidenceAvailability.NOT_APPLICABLE)
    results, _ = _evaluate_sync(
        provider, [case], ["faithfulness", "answer_relevancy"],
        run_config_fixture(), evidence=[ev],
    )
    by_name = {m.metric_name: m for m in results[0].metric_results}
    assert by_name["faithfulness"].reason == "no_retrieval_evidence"
    assert by_name["faithfulness"].score is None
    assert by_name["answer_relevancy"].score == 0.7


def test_all_attempts_failed_yields_retrieval_failed_reason():
    provider = RAGASEvalProvider(llm=MagicMock())
    case = EvalCase(id=1, input_text="q", expected_output="ref")
    ev = _evidence(attempts=[_failed_attempt(), _failed_attempt("dns")])
    results, items = _evaluate_sync(
        provider, [case], ["context_precision"], run_config_fixture(), evidence=[ev],
)
    assert results[0].metric_results[0].reason == "retrieval_failed"
    assert results[0].metric_results[0].score is None
    assert items == []


def test_zero_results_stays_a_valid_metric_input():
    """成功但 0 结果：AVAILABLE、contexts=[] 喂给 ragas，不预先 gate。"""
    provider = RAGASEvalProvider(llm=MagicMock())
    case = EvalCase(id=1, input_text="q", expected_output="ref")
    ev = _evidence(attempts=[_success_attempt(refs=())])
    results, items = _evaluate_sync(
        provider, [case], ["faithfulness"], run_config_fixture(), evidence=[ev],
)
    assert results[0].metric_results[0].score == 0.8
    assert results[0].metric_results[0].reason is None
    assert items[0]["retrieved_contexts"] == []


def test_missing_reference_gates_reference_metrics_only():
    provider = RAGASEvalProvider(llm=MagicMock())
    case = EvalCase(id=1, input_text="q", expected_output=None)
    ev = _evidence(attempts=[_success_attempt()])
    results, _ = _evaluate_sync(
        provider, [case], ["context_precision", "faithfulness"],
        run_config_fixture(), evidence=[ev],
    )
    by_name = {m.metric_name: m for m in results[0].metric_results}
    assert by_name["context_precision"].reason == "missing_reference"
    assert by_name["context_precision"].score is None
    assert by_name["faithfulness"].score == 0.8


def test_missing_actual_output_gates_output_metrics():
    provider = RAGASEvalProvider(llm=MagicMock())
    case = EvalCase(id=1, input_text="q", expected_output="ref")
    ev = EvaluationEvidence(
        example_id="example-1", run_id="run", trace_id="trace",
        input_text="q", actual_output="", expected_output="ref",
        retrieval=RetrievalEvidence(availability=EvidenceAvailability.NOT_APPLICABLE),
    )
    results, _ = _evaluate_sync(
        provider, [case], ["answer_relevancy"], run_config_fixture(), evidence=[ev],
)
    assert results[0].metric_results[0].reason == "missing_actual_output"
    assert results[0].metric_results[0].score is None


# ── Evidence summary & partial availability ─────────────────────────


def test_metric_entries_carry_bounded_evidence_summary():
    provider = RAGASEvalProvider(llm=MagicMock())
    case = EvalCase(id=1, input_text="q", expected_output="ref")
    ev = _evidence(attempts=[_failed_attempt(), _success_attempt(("ctx",))])
    results, _ = _evaluate_sync(
        provider, [case], ["faithfulness", "answer_relevancy"],
        run_config_fixture(), evidence=[ev],
    )
    for metric in results[0].metric_results:
        assert metric.evidence == {
            "availability": "available",
            "attempts": 2,
            "successful_attempts": 1,
            "contexts_used": 1,
            "reason": None,
        }


def test_partially_available_metrics_keep_overall_score_of_available_ones():
    provider = RAGASEvalProvider(llm=MagicMock())
    case = EvalCase(id=1, input_text="q", expected_output="ref")
    ev = _evidence(availability=EvidenceAvailability.UNAVAILABLE, reason="trace_unavailable")
    results, _ = _evaluate_sync(
        provider, [case], ["answer_relevancy", "context_precision"],
        run_config_fixture(), evidence=[ev],
    )
    # answer_relevancy 0.7 computes; context_precision unavailable (not 0.0).
    assert results[0].overall_score == 0.7
    by_name = {m.metric_name: m for m in results[0].metric_results}
    assert by_name["context_precision"].score is None
    assert by_name["context_precision"].passed is None


def test_retry_evidence_feeds_only_successful_contexts(captured_items):
    provider = RAGASEvalProvider(llm=MagicMock())
    case = EvalCase(id=1, input_text="q", expected_output="ref", context=["ALPHA"])
    ev = _evidence(attempts=[_failed_attempt(), _success_attempt(("BETA",))])
    results, items = _evaluate_sync(
        provider, [case], ["faithfulness"], run_config_fixture(), evidence=[ev],
)
    assert results[0].metric_results[0].score == 0.8
    assert items[0]["retrieved_contexts"] == ["BETA"]


# ── T11: DatasetExample.context is never candidate retrieved_contexts ──


def test_t11_evidence_none_never_leaks_dataset_context_to_provider(captured_items):
    """EvaluationContext.evidence=None + example.context='SOURCE_ALPHA':
    the provider must never receive SOURCE_ALPHA as retrieved_contexts."""
    import json

    from evaluation.contracts_v2 import AgentRunSummary, DatasetExample, EvaluationContext
    from evaluation.evaluators.ragas_evaluator import RagasEvaluator

    provider = RAGASEvalProvider(llm=MagicMock())
    context = EvaluationContext(
        example=DatasetExample(
            example_id="1", dataset_id="1", input_text="q",
            expected_output="ref", context=["SOURCE_ALPHA"],
        ),
        # Run with a real actual output.
        run=AgentRunSummary(
            run_id="candidate-run", input_text="q", output_text="candidate answer",
        ),
        spans=[],
        evidence=None,  # legacy caller: no canonical evidence composed
    )
    evaluator = RagasEvaluator(provider, metric_names=["faithfulness", "answer_relevancy"])

    ragas_mod = _make_ragas_module(
        evaluate_fn=lambda *a, **k: _result_with({
            "faithfulness": [0.8], "answer_relevancy": [0.7],
        }),
        dataset_cls=_capturing_dataset_cls(captured_items),
    )
    with patch.dict("sys.modules", {"ragas": ragas_mod, "ragas.metrics": ragas_mod.metrics}):
        import asyncio
        result = asyncio.run(evaluator.evaluate(context))

    # The dataset expectation string never reaches the provider as a
    # retrieval context.
    assert "SOURCE_ALPHA" not in json.dumps(captured_items)
    by_name = {m.metric_name: m for m in result.metric_results}
    assert by_name["faithfulness"].score is None
    assert by_name["faithfulness"].passed is None
    assert by_name["faithfulness"].reason == "evidence_not_provided"
    # Overall score comes only from the answer-only metric — the gated
    # retrieval metric contributes neither 0.0 nor a FAIL.
    assert result.score == 0.7
    assert by_name["answer_relevancy"].score == 0.7
