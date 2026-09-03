# Durable Run Projection Boundary

**Status: design stable, implementation deliberately incomplete.** This document is
based on `72a684f` and the current source, not on the earlier public API plan.
This change does not add an HTTP route, alter Trace storage, or make
`AgentExecutionAudit` authoritative.

## Ownership

Run projection belongs to an **execution projection boundary** in the
framework-neutral `application.execution.run_projection` module. It is a
read-side capability, not Runtime semantics and not Observability semantics.
The module currently provides the small `RunRecord`, `RunReader`, `RunWriter`,
`RunProjector`, and reference `InMemoryRunStore` contracts. A backend-owned
Postgres adapter and composition-root wiring are intentionally deferred.

Runtime remains the only owner of execution facts and identity. The projector
never generates `run_id`, `trace_id`, span IDs, status, timestamps, or terminal
outcomes.

## Current fact flow

```text
ExecuteAgent.execute/stream
  -> RunExecutor (backend AgentRuntimeExecutor)
  -> AgentRuntime.run()/stream()
  -> ExecutionContext (created at the Runtime boundary)
  -> AgentRun (blocking result) + RuntimeEvent v2
  -> runtime EventBus (awaited, in-process, subscription order)
  -> Runtime completion sink receives the terminal AgentRun snapshot
  -> Trace/Cost listeners today; RunProjector remains an injectable application sink
```

`run()` constructs `ExecutionContext` and an `AgentRun`; `run_turn()` emits
`RunStarted` and the terminal event, while `run()` emits the normal terminal
event after the turn and publishes the snapshot. `stream()` creates the
context, `stream_turn()` emits its lifecycle, and Runtime builds/publishes the
terminal `AgentRun` after the stream completes (or with failed/cancelled status
when it terminates exceptionally). The `EventBus` catches and logs listener
exceptions, allowing subsequent listeners and Runtime execution to continue.

The legacy `AgentEvent` bus is also used for UI/stream updates. The v2 events
are emitted on that same bus; an SSE adapter is therefore not an acceptable
place to persist a Run.

## Are RuntimeEvents sufficient?

No. They are sufficient for the minimal lifecycle skeleton, but not for the
complete `AgentRun` read model:

| Run fact | AgentRun | RuntimeEvent | Safe in event-only v1? |
|---|---:|---|---:|
| `run_id` / `trace_id` | yes | all v2 events | yes |
| lifecycle status | yes | started + terminal event | yes |
| target type/key/version | yes | key/version only on `RunStarted` | key/version only; type is missing |
| input | yes | `RunStarted.input_text` | yes, as text |
| output | yes | `RunCompleted.output_text` | completed only |
| started/completed time | yes | event timestamps | yes |
| duration | yes | completed has a field, failed/cancelled do not | only when explicitly supplied |
| error code/message | yes | `RunFailed` | yes for failed |
| session ID | yes | `RunStarted` | yes |
| metadata | yes | `attributes` on selected events | incomplete |
| action/handoff/chain/skills | yes | not on Run lifecycle events | no |
| usage/tool summary | yes | call-level events exist, but no Run aggregate | not in minimal v1 |
| user ID | request/runtime context | absent from Run lifecycle events | no |

The projector therefore never reconstructs target type, duration, usage, tool
summary, metadata, or output from Trace. Missing fields stay `None` (or the
explicit empty value delivered by Runtime).

## Events plus terminal snapshot

The selected source model is **events plus terminal `AgentRun` snapshot**:

1. `RunStarted` creates the running row and supplies identity, input, target
   key/version, session, and start time.
2. A terminal event supplies lifecycle status and terminal event time. It is
   enough to expose a minimal skeleton even if the caller does not retain the
   returned `AgentRun`.
3. The returned terminal `AgentRun` is required to finalize the full durable
   row: target type, arbitrary input/output, authoritative `finished_at`,
   duration, metadata, and usage-related fields when those are later admitted
   to the schema.

`finalize(AgentRun)` is intentionally a writer capability, not a callback into
Runtime. The Runtime owns the terminal snapshot. Its framework-neutral
completion sink may pass that snapshot to a projector for blocking and
streaming executions; sink/storage failures are logged as projection
failures and never change the already-emitted Runtime terminal status. It must
not be attached only to an HTTP/SSE adapter: SSE/backend never reconstructs an
`AgentRun` from events.

## Run v1 model and status rules

`RunRecord` currently contains identity, lifecycle status, target fields,
input/output, timestamps, duration, session, error, metadata, and projection
metadata. `projected_at`, `updated_at`, and `projection_version` are read-model
metadata, not Runtime facts. `status` is lifecycle state (`running`,
`completed`, `failed`, `cancelled`); an outcome such as guardrail `blocked`
remains metadata and does not become Runtime failure. `outcome` is not added
until Runtime exposes a stable typed field.

Legal lifecycle transitions are `running -> completed|failed|cancelled`.
Duplicate starts do not reset a row. A terminal event without a start is quarantined/logged, but is **not** marked
as successfully applied. Re-delivery after `RunStarted` (or an explicit retry)
projects the same event and clears its quarantine entry. A late non-terminal
event has no Run v1 effect. A repeated terminal with the same facts is
idempotent; a conflicting terminal raises a projection conflict for
quarantine/retry handling rather than silently replacing the authoritative
result. Quarantine is a projection recovery mechanism only; it is not Runtime,
AgentRun, or public Run API semantics.

## Snapshot merge and identity rules

`run_id` and `trace_id` are immutable authoritative identity. A matching value
is accepted; a missing value may be filled when the source explicitly supplies
it; a different value raises `RunProjectionConflict` and leaves the existing
record untouched. Lookup and storage always use the same `run_id`.

Terminal snapshots may complement the lifecycle skeleton with target type,
target key/version, input/output, timestamps, duration, session, metadata, and
error facts. Projection metadata (`projected_at`, `updated_at`, and version)
is owned by the projection. Nullable facts are tested with `is None`, never
truthiness: `0`, `0.0`, `""`, `[]`, `{}`, and `False` remain valid explicit
values. Missing facts remain missing.

## Idempotency, ordering, and consistency

The current event contract has `event_id`, so the writer deduplicates it. A
Postgres implementation must persist a processed-event key or use an
atomic/upsert equivalent; `run_id` remains the aggregate primary key and is
not an event identity.

There is no sequence number or monotonic ordering field in `RuntimeEvent`.
Current ordering is guaranteed only by the awaited, in-process EventBus
subscription order. This is **not** a distributed ordering guarantee. A
future durable delivery mechanism must either preserve order per `run_id` or
quarantine/retry a terminal-before-start delivery.

Runtime completion is independent of projection persistence. The current bus
logs listener failures; a durable adapter must add retry/replay/dead-letter
handling rather than silently discard failed writes. Until that adapter exists,
there is no rebuild guarantee and the in-memory proof is not authoritative.

The intended production read consistency is synchronous enough that the Runtime
boundary projects/finalizes before its execution result is considered visible
to the application. This is a future wiring decision; the current proof is
not wired and therefore provides no GET-after-execute guarantee.

## Storage boundary

The future table must be separate from `trace_records` and
`agent_execution_audits`, with `run_id` as the primary key, separately indexed
`trace_id`, typed status, target columns, JSON input/output/metadata, lifecycle
 timestamps, and error columns. JSON is an opaque durable payload contract,
not a place to pickle arbitrary Runtime objects. Retention/redaction of user
input and model output must be decided before production persistence.

### Run vs Trace vs Audit

| Concern | Run projection | Trace projection | AgentExecutionAudit |
|---|---|---|---|
| Purpose | execution resource | diagnostics | legacy per-agent audit/compatibility |
| Identity | `run_id` | `trace_id` (+ reference to run) | legacy `run_id` string |
| Cardinality | one per Run | one trace with spans | historically one audit row per turn |
| Facts | lifecycle/final Runtime facts | detailed spans/events | incomplete legacy summary |
| Public API role | future Run API | observability API | not authoritative |

A Run is never constructed from Trace, and `run_id` is never replaced with
`trace_id`. `AgentExecutionAudit` is not used by this boundary.

## Reader contract and future adapter

The narrow contract is:

```python
class RunReader(Protocol):
    async def get_run(self, run_id: str) -> RunRecord | None: ...
```

A future route can consequently be deliberately boring:

```python
run = await reader.get_run(run_id)
if run is None:
    raise HTTPException(404)
return map_run_response(run)
```

No Trace lookup, status calculation, identity fallback, or Runtime invocation
belongs in that adapter.

## Historical Runs and readiness

Runs created before this projection exists are **not supported**. No Trace or
Audit backfill is attempted because the required facts are not authoritative
there.

`GET /api/runs/{run_id}` is **not yet safe to implement**: no durable store,
migration, or production composition wiring exists yet. The framework-neutral
projection contract, retry semantics, and blocking/streaming Runtime snapshot
boundary are stable. The correct verdict for this slice is:

> **CONTRACT STABLE, DURABLE PERSISTENCE DEFERRED**
