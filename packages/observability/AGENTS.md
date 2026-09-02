<!-- Parent: ../../AGENTS.md -->

# observability

## Purpose

Observability observes Runtime execution. It projects semantic `RuntimeEvent` facts into `Trace` and `Span` records for querying and diagnostics; it does not define or execute a Run.

## Responsibilities

- Consume `RuntimeEvent` through the EventBus or `TraceProjector`.
- Preserve Runtime-provided `run_id`, `trace_id`, `span_id`, and `parent_span_id`.
- Correlate start/completion/failure events into spans and finalize a Trace at the Run terminal event.
- Diagnose malformed, unknown, duplicate-start, and orphan-completion events while degrading safely.

## Projector rules

Projectors must **not** generate `run_id`, `trace_id`, `span_id`, or `parent_span_id`, guess parents, or infer operation identity from names/order. Explicit Runtime identity always wins. A missing identity is malformed input, not permission to fabricate one.

One operation maps to one span identity. Multiple semantic events may enrich one span—for example `GuardrailEvaluated` followed by `GuardrailBlocked`—without creating a second span. `span_id` is unique within a Trace.

A `Trace` is an observability projection of an `AgentRun`; `Run != Trace`. The Run lifecycle is owned by `agent_runtime`, and the projector waits for `RunCompleted`, `RunFailed`, or `RunCancelled` to finalize the root Trace.

## Dependency rules

- Consume the Runtime event contract; do not import or control Runtime internals.
- Do not depend on Evaluation or Compare.
- Keep storage and HTTP concerns behind `TraceStore`/module interfaces.

## Testing expectations

Cover identity and parent preservation, one-span-per-operation, event enrichment, duplicate span IDs, orphan completions, malformed/unknown events, open-span finalization, and all terminal statuses. See `tests/test_projector.py` and `tests/test_span_processor.py`.

## Key files

- `src/observability/projector.py` — pure RuntimeEvent-to-Trace projection.
- `src/observability/contracts.py` — Trace/Span contracts.
- `src/observability/trace_store.py` — Trace persistence protocol.
