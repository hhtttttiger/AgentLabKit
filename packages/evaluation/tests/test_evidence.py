"""Evaluation Evidence Composition — canonical evidence 语义测试。

覆盖 §30 failure matrix 中 composer 层的场景：
no retrieval / success with results / zero results / failed retrieval /
retry / trace unavailable，以及 identity truth（composer 只 carry identity）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from evaluation.evidence import (
    EvidenceAvailability,
    REASON_TRACE_UNAVAILABLE,
    compose_evaluation_evidence,
)


@dataclass
class Example:
    example_id: str = "example-1"
    dataset_id: str = "dataset-1"
    input_text: str = "When is Project Falcon deployed?"
    expected_output: str | None = "Tuesday 03:00 UTC"
    context: list = field(default_factory=list)
    source_run_id: str | None = None
    source_trace_id: str | None = None


@dataclass
class Run:
    run_id: str = "candidate-run-id"
    trace_id: str | None = "candidate-trace-id"
    output: object = "Tuesday 03:00 UTC"


def _span(
    span_id: str = "s1",
    name: str = "retrieval.search",
    kind: str = "retrieval",
    status: str = "ok",
    attributes: dict | None = None,
    error_message: str | None = None,
):
    return type(
        "Span",
        (),
        {
            "span_id": span_id, "name": name, "kind": kind,
            "duration_ms": 5, "status": status,
            "attributes": attributes or {},
            "error_message": error_message,
        },
    )()


def _ref(preview: str, score: float = 0.9):
    return {
        "knowledge_base_id": "kb-1", "document_id": f"doc-{preview}",
        "segment_id": "seg-1", "score": score, "title": preview,
        "source": "falcon.md", "content_preview": preview,
    }


# ── Trace availability ───────────────────────────────────────────────


def test_missing_trace_is_unavailable_not_applicable():
    evidence = compose_evaluation_evidence(example=Example(), run=Run(), spans=[])
    assert evidence.retrieval.availability is EvidenceAvailability.UNAVAILABLE
    assert evidence.retrieval.reason == REASON_TRACE_UNAVAILABLE
    assert evidence.retrieval.contexts == ()


def test_none_spans_is_unavailable():
    evidence = compose_evaluation_evidence(example=Example(), run=Run(), spans=None)
    assert evidence.retrieval.availability is EvidenceAvailability.UNAVAILABLE


# ── No retrieval ─────────────────────────────────────────────────────


def test_trace_without_retrieval_spans_is_not_applicable():
    spans = [_span(span_id="root", name="agent.run", kind="RUN")]
    evidence = compose_evaluation_evidence(example=Example(), run=Run(), spans=spans)
    assert evidence.retrieval.availability is EvidenceAvailability.NOT_APPLICABLE
    assert evidence.retrieval.reason is None
    assert evidence.retrieval.attempts == ()
    assert evidence.retrieval.contexts == ()


# ── Success with results ─────────────────────────────────────────────


def test_successful_retrieval_composes_candidate_contexts():
    spans = [
        _span(attributes={
            "retrieval.query": "Falcon deployment",
            "retrieval.result_count": 2,
            "retrieval.results": [_ref("ctx-1"), _ref("ctx-2")],
        }),
    ]
    evidence = compose_evaluation_evidence(example=Example(), run=Run(), spans=spans)
    assert evidence.retrieval.availability is EvidenceAvailability.AVAILABLE
    assert evidence.retrieval.successful_attempts == 1
    assert evidence.retrieval.contexts == ("ctx-1", "ctx-2")


def test_candidate_contexts_are_bounded_refs_in_execution_order():
    # Spans arrive in trace-store order (= execution order).  Within one
    # attempt refs keep their given order and are NOT re-ranked by score.
    spans = [
        _span(span_id="r2", attributes={
            "retrieval.result_count": 2,
            "retrieval.results": [_ref("second", 0.5), _ref("first", 0.9)],
        }),
        _span(span_id="r1", attributes={
            "retrieval.result_count": 1,
            "retrieval.results": [_ref("earlier", 1.0)],
        }),
    ]
    evidence = compose_evaluation_evidence(example=Example(), run=Run(), spans=spans)
    assert evidence.retrieval.contexts == ("second", "first", "earlier")


# ── Zero results is available, not unavailable ───────────────────────


def test_successful_retrieval_with_zero_results_stays_available():
    spans = [_span(attributes={
        "retrieval.result_count": 0,
        "retrieval.results": [],
    })]
    evidence = compose_evaluation_evidence(example=Example(), run=Run(), spans=spans)
    assert evidence.retrieval.availability is EvidenceAvailability.AVAILABLE
    assert evidence.retrieval.reason is None
    assert evidence.retrieval.successful_attempts == 1
    assert evidence.retrieval.contexts == ()


# ── Failure ──────────────────────────────────────────────────────────


def test_failed_retrieval_is_represented_without_invented_contexts():
    spans = [_span(
        status="error",
        error_message="vector store down",
        attributes={"retrieval.error_message": "vector store down"},
    )]
    evidence = compose_evaluation_evidence(example=Example(), run=Run(), spans=spans)
    assert evidence.retrieval.availability is EvidenceAvailability.AVAILABLE
    assert evidence.retrieval.successful_attempts == 0
    assert evidence.retrieval.contexts == ()
    assert evidence.retrieval.attempts[0].succeeded is False
    assert evidence.retrieval.attempts[0].error_message == "vector store down"


# ── Retry: failed attempt + successful retry ─────────────────────────


def test_retry_keeps_attempt_boundaries_and_successful_contexts():
    spans = [
        _span(span_id="attempt-1", status="error", attributes={
            "retrieval.error_message": "timeout",
        }),
        _span(span_id="attempt-2", attributes={
            "retrieval.result_count": 1,
            "retrieval.results": [_ref("retry-context")],
        }),
    ]
    evidence = compose_evaluation_evidence(example=Example(), run=Run(), spans=spans)
    assert evidence.retrieval.availability is EvidenceAvailability.AVAILABLE
    assert len(evidence.retrieval.attempts) == 2
    assert [a.succeeded for a in evidence.retrieval.attempts] == [False, True]
    # Metric contexts consume only the successful retry — no double count.
    assert evidence.retrieval.contexts == ("retry-context",)
    assert evidence.retrieval.successful_attempts == 1


# ── Identity & ownership ─────────────────────────────────────────────


def test_composer_carries_identity_and_never_invents_it():
    example = Example(
        source_run_id="source-run-a", source_trace_id="source-trace-a",
    )
    evidence = compose_evaluation_evidence(
        example=example, run=Run("candidate-run-b", "candidate-trace-b"), spans=[],
    )
    assert evidence.run_id == "candidate-run-b"
    assert evidence.trace_id == "candidate-trace-b"
    assert evidence.example_id == "example-1"
    # Capture provenance never leaks into candidate evidence identity.
    assert "source-run-a" not in (evidence.run_id or "")
    assert "source-trace-a" not in (evidence.trace_id or "")


def test_composer_without_run_has_no_identity():
    evidence = compose_evaluation_evidence(example=Example(), run=None, spans=None)
    assert evidence.run_id is None
    assert evidence.trace_id is None
    assert evidence.actual_output is None


def test_composer_owns_expectation_vs_actual_split():
    evidence = compose_evaluation_evidence(
        example=Example(expected_output="Tuesday 03:00 UTC"),
        run=Run(output="It deploys Tuesday 03:00 UTC."),
        spans=[],
    )
    assert evidence.expected_output == "Tuesday 03:00 UTC"
    assert evidence.actual_output == "It deploys Tuesday 03:00 UTC."
    assert evidence.input_text == "When is Project Falcon deployed?"


def test_failed_run_has_none_actual_output_not_empty_string():
    evidence = compose_evaluation_evidence(
        example=Example(), run=Run(output=None), spans=[],
    )
    assert evidence.actual_output is None


def test_retrieval_summary_is_bounded():
    spans = [
        _span(span_id="a1", status="error", attributes={"retrieval.error_message": "x"}),
        _span(span_id="a2", attributes={
            "retrieval.result_count": 2,
            "retrieval.results": [_ref("r1"), _ref("r2")],
        }),
    ]
    evidence = compose_evaluation_evidence(example=Example(), run=Run(), spans=spans)
    summary = evidence.retrieval_summary()
    assert summary == {
        "availability": "available",
        "attempts": 2,
        "successful_attempts": 1,
        "contexts_used": 2,
        "reason": None,
    }


def test_string_encoded_refs_are_decoded():
    import json

    spans = [_span(attributes={
        "retrieval.result_count": 1,
        "retrieval.results": json.dumps([_ref("embedded")]),
    })]
    evidence = compose_evaluation_evidence(example=Example(), run=Run(), spans=spans)
    assert evidence.retrieval.contexts == ("embedded",)


def test_result_count_without_refs_does_not_invent_contexts():
    spans = [_span(attributes={"retrieval.result_count": 3})]
    evidence = compose_evaluation_evidence(example=Example(), run=Run(), spans=spans)
    assert evidence.retrieval.availability is EvidenceAvailability.AVAILABLE
    assert evidence.retrieval.successful_attempts == 1
    assert evidence.retrieval.contexts == ()


@pytest.mark.parametrize("kind,name", [
    ("retrieval", "retrieval.search"),
    ("RETRIEVAL", "retrieval.query"),
    ("", "retrieval.search"),
])
def test_retrieval_spans_recognized_across_projection_shapes(kind, name):
    spans = [_span(kind=kind, name=name, attributes={
        "retrieval.results": [_ref("ctx")],
    })]
    evidence = compose_evaluation_evidence(example=Example(), run=Run(), spans=spans)
    assert evidence.retrieval.successful_attempts == 1
