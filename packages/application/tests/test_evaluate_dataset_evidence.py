"""Candidate evidence provenance regression tests (phase: Evaluation Evidence
Composition v1).

§31 Critical provenance: Source Run A (retrieved "ALPHA") captured as example E;
candidate Run B retrieves "BETA" — the metric MUST receive "BETA" and NEVER
"ALPHA".

§32 Candidate isolation: two evaluation runs over the same example each bind
their own candidate evidence.

§33 Trace truth: evidence run_id/trace_id are exactly the Runtime-owned
candidate identities.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from application.evaluation import EvaluateDataset, EvaluateDatasetCommand
from evaluation.contracts_v2 import (
    DatasetExample, EvaluationContext, EvaluationResult, TraceProjection,
)
from evaluation.evidence import EvidenceAvailability


@dataclass
class Example:
    example_id: str = "dataset-owned-example-id"
    dataset_id: str = "dataset-1"
    input_text: str = "When is Project Falcon deployed?"
    expected_output: str | None = "Tuesday 03:00 UTC"
    context: list = field(default_factory=list)
    source_run_id: str | None = "source-run-A"
    source_trace_id: str | None = "source-trace-A"


class Agents:
    async def resolve(self, key):
        return f"target:{key}"


class Executor:
    """Executes candidate runs with Runtime-owned identity."""

    def __init__(self, runs):
        self._runs = list(runs)
        self.calls = 0

    async def execute(self, **kwargs):
        run = self._runs[min(self.calls, len(self._runs) - 1)]
        self.calls += 1
        return run


@dataclass
class CandidateRun:
    run_id: str
    trace_id: str
    output: object = "candidate answer"


@dataclass
class Span:
    span_id: str
    name: str = "retrieval.search"
    kind: str = "retrieval"
    status: str = "ok"
    duration_ms: int = 1
    error_message: str | None = None
    attributes: dict = field(default_factory=dict)


class TraceStore:
    """Trace projection keyed by the Runtime-owned candidate trace_id."""

    def __init__(self, traces, dropped_span_counts=None):
        self._traces = traces
        self._dropped = dropped_span_counts or {}

    async def get_trace_projection(self, trace_id):
        spans = self._traces.get(trace_id)
        if spans is None:
            return None
        return TraceProjection(
            spans=spans, dropped_span_count=self._dropped.get(trace_id, 0),
        )


class Store:
    def __init__(self):
        self.recorded = []
        self.completed = False

    async def start(self, **kwargs):
        return object()

    async def record_result(self, run, result):
        self.recorded.append(result)

    async def complete(self, run):
        self.completed = True
        return run

    async def fail(self, run, error):
        raise AssertionError(f"evaluation run failed: {error}")


class CapturingEvaluator:
    """Stands in for the metric provider and records what it received."""

    def __init__(self):
        self.contexts = []

    async def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        self.contexts.append(context)
        return EvaluationResult(
            example_id=context.example.example_id,
            run_id=context.run.run_id if context.run else None,
            passed=True,
            score=1.0,
        )


def _candidate_spans(preview: str) -> list[Span]:
    return [Span(
        span_id="retrieval-span-1",
        attributes={
            "retrieval.query": "Falcon deployment",
            "retrieval.result_count": 1,
            "retrieval.results": [{
                "knowledge_base_id": "kb-1", "document_id": "doc-falcon",
                "segment_id": "seg-1", "score": 0.9,
                "title": "falcon", "source": "falcon.md",
                "content_preview": preview,
            }],
        },
    )]


async def _run_evaluation(examples, runs, traces, evaluator):
    store = Store()
    await EvaluateDataset(
        _DatasetReader(examples), Agents(), Executor(runs), evaluator, store,
        traces=TraceStore(traces),
    ).execute(EvaluateDatasetCommand("dataset-1", "agent"))
    return store


class _DatasetReader:
    def __init__(self, examples):
        self._examples = examples

    async def get_examples(self, dataset_id):
        return self._examples


# ── §31 Critical provenance ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_metric_receives_candidate_context_never_source_context():
    # Source Run A retrieved "ALPHA" and was captured as example E.
    example = Example(context=["ALPHA"])
    # Candidate Run B retrieves "BETA".
    candidate = CandidateRun("candidate-run-B", "candidate-trace-B", output="answer B")
    traces = {"candidate-trace-B": _candidate_spans("BETA")}
    evaluator = CapturingEvaluator()

    await _run_evaluation([example], [candidate], traces, evaluator)

    context = evaluator.contexts[0]
    retrieval = context.evidence.retrieval
    assert retrieval.contexts == ("BETA",)
    assert all("ALPHA" not in c for c in retrieval.contexts), (
        "metric input must never contain capture-source retrieval context"
    )
    # The provider-visible contexts mirror the evidence, not example.context.
    assert example.context == ["ALPHA"]  # dataset expectation unchanged
    assert context.evidence.expected_output == "Tuesday 03:00 UTC"
    assert context.evidence.actual_output == "answer B"


# ── §32 Candidate isolation ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_two_candidates_bind_their_own_evidence():
    example = Example()
    traces = {
        "trace-1": _candidate_spans("A"),
        "trace-2": _candidate_spans("B"),
    }

    first_evaluator = CapturingEvaluator()
    await _run_evaluation(
        [example], [CandidateRun("run-1", "trace-1", output="answer 1")],
        traces, first_evaluator,
    )
    second_evaluator = CapturingEvaluator()
    await _run_evaluation(
        [example], [CandidateRun("run-2", "trace-2", output="answer 2")],
        traces, second_evaluator,
    )

    first_evidence = first_evaluator.contexts[0].evidence
    second_evidence = second_evaluator.contexts[0].evidence
    assert first_evidence.retrieval.contexts == ("A",)
    assert second_evidence.retrieval.contexts == ("B",)
    assert first_evidence.run_id == "run-1"
    assert second_evidence.run_id == "run-2"
    # Same dataset example evaluated twice — no evidence reuse/caching.
    assert first_evidence.example_id == second_evidence.example_id


# ── §33 Trace identity truth ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_evidence_identity_equals_runtime_candidate_identity():
    example = Example()
    candidate = CandidateRun("runtime-run-id", "runtime-trace-id")
    traces = {"runtime-trace-id": _candidate_spans("BETA")}
    evaluator = CapturingEvaluator()

    await _run_evaluation([example], [candidate], traces, evaluator)

    evidence = evaluator.contexts[0].evidence
    assert evidence.run_id == candidate.run_id
    assert evidence.trace_id == candidate.trace_id
    # Opaque string identity; the dataset-owned example_id is a different
    # namespace entirely.
    assert evidence.example_id == "dataset-owned-example-id"
    assert evidence.example_id != evidence.run_id


@pytest.mark.asyncio
async def test_evaluation_completes_when_trace_unavailable():
    example = Example()
    candidate = CandidateRun("run-1", "trace-1")
    evaluator = CapturingEvaluator()

    store = await _run_evaluation([example], [candidate], {}, evaluator)

    evidence = evaluator.contexts[0].evidence
    assert evidence.retrieval.availability is EvidenceAvailability.UNAVAILABLE
    assert evidence.retrieval.reason == "trace_unavailable"
    assert store.completed
    assert store.recorded[0].score == 1.0  # answer-only evaluation still works


@pytest.mark.asyncio
async def test_no_retrieval_is_reported_not_applicable():
    example = Example()
    candidate = CandidateRun("run-1", "trace-1")
    traces = {"trace-1": [Span(span_id="root", name="agent.run", kind="RUN")]}
    evaluator = CapturingEvaluator()

    await _run_evaluation([example], [candidate], traces, evaluator)

    evidence = evaluator.contexts[0].evidence
    assert evidence.retrieval.availability is EvidenceAvailability.NOT_APPLICABLE


@pytest.mark.asyncio
async def test_retry_evidence_preserved_for_candidate():
    example = Example()
    candidate = CandidateRun("run-1", "trace-1")
    traces = {"trace-1": [
        Span(span_id="a1", status="error", error_message="timeout",
             attributes={"retrieval.error_message": "timeout"}),
        Span(span_id="a2", attributes={
            "retrieval.result_count": 1,
            "retrieval.results": [{"content_preview": "BETA"}],
        }),
    ]}
    evaluator = CapturingEvaluator()

    await _run_evaluation([example], [candidate], traces, evaluator)

    retrieval = evaluator.contexts[0].evidence.retrieval
    assert [a.succeeded for a in retrieval.attempts] == [False, True]
    assert retrieval.contexts == ("BETA",)


# ── Trace truncation truthfulness (closeout EF-02) ───────────────────


@pytest.mark.asyncio
async def test_truncated_trace_zero_visible_retrieval_spans_is_unavailable_not_applicable():
    example = Example()
    candidate = CandidateRun("run-1", "trace-1")
    traces = {"trace-1": [Span(span_id="root", name="agent.run", kind="RUN")]}
    store = Store()
    traces_store = TraceStore(
        traces, dropped_span_counts={"trace-1": 3},
    )
    evaluator = CapturingEvaluator()
    await EvaluateDataset(
        _DatasetReader([example]), Agents(), Executor([candidate]), evaluator,
        store, traces=traces_store,
    ).execute(EvaluateDatasetCommand("dataset-1", "agent"))

    retrieval = evaluator.contexts[0].evidence.retrieval
    assert retrieval.availability is EvidenceAvailability.UNAVAILABLE
    assert retrieval.reason == "trace_incomplete"


@pytest.mark.asyncio
async def test_truncated_trace_with_visible_retrieval_keeps_incomplete_state():
    example = Example()
    candidate = CandidateRun("run-1", "trace-1")
    traces = {"trace-1": _candidate_spans("BETA")}
    store = Store()
    traces_store = TraceStore(
        traces, dropped_span_counts={"trace-1": 2},
    )
    evaluator = CapturingEvaluator()
    await EvaluateDataset(
        _DatasetReader([example]), Agents(), Executor([candidate]), evaluator,
        store, traces=traces_store,
    ).execute(EvaluateDatasetCommand("dataset-1", "agent"))

    evidence = evaluator.contexts[0].evidence
    retrieval = evidence.retrieval
    # Existing authoritative retrieval evidence stays usable...
    assert retrieval.availability is EvidenceAvailability.AVAILABLE
    assert retrieval.contexts == ("BETA",)
    # ...but the summary preserves the incompleteness truth.
    assert retrieval.reason == "trace_incomplete"
    assert evidence.retrieval_summary()["reason"] == "trace_incomplete"


# ── Candidate trace finalization (closeout EF-01) ────────────────────


class RecordingFinalization:
    """Narrow seam stand-in: records the awaited trace ids and result."""

    def __init__(self, result: bool = True, delay: float = 0.0):
        self.result = result
        self.delay = delay
        self.awaited: list[str] = []
        self.timeouts: list[float] = []

    async def wait_until_persisted(self, trace_id: str, *, timeout_seconds: float) -> bool:
        import asyncio
        self.awaited.append(trace_id)
        self.timeouts.append(timeout_seconds)
        if self.delay:
            await asyncio.sleep(self.delay)
        return self.result


@pytest.mark.asyncio
async def test_finalization_is_awaited_for_candidate_trace_before_read():
    candidate = CandidateRun("candidate-run-b", "candidate-trace-b")
    traces = {"candidate-trace-b": _candidate_spans("BETA")}
    run_store = Store()

    class OrderTrackingTraceStore(TraceStore):
        """Asserts the projection is read only after finalization is awaited."""

        def __init__(self, traces):
            super().__init__(traces)
            self.events: list[tuple[str, str]] = []

        async def get_trace_projection(self, trace_id):
            self.events.append(("read", trace_id))
            return await super().get_trace_projection(trace_id)

    class OrderedFinalization(RecordingFinalization):
        async def wait_until_persisted(self, trace_id, *, timeout_seconds):
            trace_store.events.append(("wait", trace_id))
            return await super().wait_until_persisted(trace_id, timeout_seconds=timeout_seconds)

    trace_store = OrderTrackingTraceStore(traces)
    finalization = OrderedFinalization(result=True)
    evaluator = CapturingEvaluator()

    await EvaluateDataset(
        _DatasetReader([Example()]), Agents(), Executor([candidate]), evaluator,
        run_store, traces=trace_store,
        finalization=finalization,
        trace_finalization_timeout_seconds=5.0,
    ).execute(EvaluateDatasetCommand("dataset-1", "agent"))

    # Candidate trace_id only — never any other id, never a fallback.
    assert finalization.awaited == ["candidate-trace-b"]
    assert finalization.timeouts == [5.0]
    # Ordering: the wait precedes the projection read for that trace.
    assert ("wait", "candidate-trace-b") in trace_store.events
    assert trace_store.events.index(("wait", "candidate-trace-b")) < trace_store.events.index(("read", "candidate-trace-b"))
    # Evidence still composes from the authoritative trace.
    assert evaluator.contexts[0].evidence.retrieval.contexts == ("BETA",)


@pytest.mark.asyncio
async def test_finalization_timeout_yields_unavailable_evidence_run_continues():
    candidate = CandidateRun("run-1", "trace-1")
    evaluator = CapturingEvaluator()
    store = Store()

    await EvaluateDataset(
        _DatasetReader([Example()]), Agents(), Executor([candidate]), evaluator,
        store, traces=TraceStore({}),
        finalization=RecordingFinalization(result=False),
        trace_finalization_timeout_seconds=0.01,
    ).execute(EvaluateDatasetCommand("dataset-1", "agent"))

    evidence = evaluator.contexts[0].evidence
    assert evidence.retrieval.availability is EvidenceAvailability.UNAVAILABLE
    assert evidence.retrieval.reason == "trace_finalization_timeout"
    # The evaluation run completes; answer-only evaluation still recorded.
    assert store.completed
    assert store.recorded[0].score == 1.0


@pytest.mark.asyncio
async def test_late_trace_persistence_after_timeout_is_still_truth():
    """A trace that lands after the bounded wait is still an authoritative
    fact — it is read and composed (not discarded because the ACK was late)."""
    candidate = CandidateRun("run-1", "trace-1")
    traces = {"trace-1": _candidate_spans("BETA")}
    evaluator = CapturingEvaluator()
    store = Store()

    await EvaluateDataset(
        _DatasetReader([Example()]), Agents(), Executor([candidate]), evaluator,
        store, traces=TraceStore(traces),
        finalization=RecordingFinalization(result=False),
        trace_finalization_timeout_seconds=0.01,
    ).execute(EvaluateDatasetCommand("dataset-1", "agent"))

    evidence = evaluator.contexts[0].evidence
    assert evidence.retrieval.availability is EvidenceAvailability.AVAILABLE
    assert evidence.retrieval.contexts == ("BETA",)


@pytest.mark.asyncio
async def test_finalization_cancellation_propagates_immediately():
    import asyncio

    class CancellingFinalization:
        async def wait_until_persisted(self, trace_id, *, timeout_seconds):
            await asyncio.sleep(30)

    candidate = CandidateRun("run-1", "trace-1")
    evaluator = CapturingEvaluator()

    task = asyncio.create_task(EvaluateDataset(
        _DatasetReader([Example()]), Agents(), Executor([candidate]), evaluator,
        Store(), traces=TraceStore({}),
        finalization=CancellingFinalization(),
    ).execute(EvaluateDatasetCommand("dataset-1", "agent")))
    await asyncio.sleep(0.1)
    task.cancel()
    import pytest as _pytest
    with _pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, timeout=2.0)
