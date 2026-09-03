# Durable Run Projection Boundary

**Status: durable persistence, production wiring, and the public read adapter are
complete.** `GET /api/runs/{run_id}` consumes `RunReader` directly. This document is
based on the current source. This slice does not add an HTTP route, alter Trace
storage, or make `AgentExecutionAudit` authoritative.

## Ownership

Run projection belongs to an **execution projection boundary** in the
framework-neutral `application.execution.run_projection` module. It is a
read-side capability, not Runtime semantics and not Observability semantics.
The module provides the small `RunRecord`, `RunReader`, `RunWriter`,
`RunProjector`, and reference `InMemoryRunStore` contracts. The SQLAlchemy
implementation is in `backend/src/modules/run_projection/` (`RunRecordModel`,
`RunProjectionEventModel`, and `SqlAlchemyRunStore`). Migration `0020` creates
`run_records` and the durable event-id ledger `run_projection_events`.

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
  -> sibling RunProjector listener and Trace/Cost consumers
  -> durable RunRecord row; completion sink finalizes the same row
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
handling rather than silently discard failed writes. The current adapter logs
failures and leaves Runtime truth unchanged; there is no distributed rebuild
or replay guarantee.

Production wiring is in `backend/src/runtime/web_modules.py`: the same
`SqlAlchemyRunStore` is subscribed to the Runtime EventBus and its `finalize`
method is injected as the Runtime completion sink. Event listeners are awaited
in the current in-process bus, while the Runtime deliberately catches and logs
projection failures. Therefore successful projection is synchronously readable
after execution returns, but the overall guarantee is **best-effort synchronous
side effect**, not exactly-once delivery or a guarantee during database outage.
Runtime status and SSE terminal truth are never changed by projection failure.
The stable `RuntimeEvent.event_id` is persisted for durable redelivery
idempotency. There is no durable orphan quarantine table: production delivery is
ordered in-process; an orphan is surfaced/logged and its transaction rolls back.

## Storage boundary

The durable `run_records` table is separate from `trace_records` and
`agent_execution_audits`. `run_id` is its primary key; `trace_id` is only an
indexed association. It stores canonical status, target columns, JSONB
input/output/metadata, lifecycle timestamps, duration, and error fields.
`run_projection_events.event_id` is the durable idempotency key. Payloads are
normalized to JSON-safe values and unknown objects fail loudly; no pickle,
repr, or exception object is stored. RunStore contains user/model execution
payloads. Existing application database lifecycle is the current retention
policy; no additional redaction or TTL subsystem exists yet.

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

## Reader contract and HTTP adapter

The narrow contract is:

```python
class RunReader(Protocol):
    async def get_run(self, run_id: str) -> RunRecord | None: ...
```

A route can consequently be deliberately boring:

```python
run = await reader.get_run(run_id)
if run is None:
    raise HTTPException(404)
return map_run_response(run)
```

No Trace lookup, status calculation, identity fallback, or Runtime invocation
belongs in that adapter.

## HTTP read adapter

The backend exposes `GET /api/runs/{run_id}` as a deliberately thin adapter.
It maps the durable `RunRecord` through the explicit `run_record_to_response()`
mapper; Runtime results use the separate `agent_run_to_response()` mapper. The
mappers do not read Trace, AgentExecutionAudit, or Runtime state. The endpoint
authorizes against persisted `RunRecord.user_id` only: the owner may read,
while missing or mismatched ownership returns 404. Legacy null-owner rows remain
inaccessible. List Runs remains deferred; Replay applies the same source-run
check before execution.

## Historical Runs and readiness

Runs created before this projection exists are **not supported**. No Trace or
Audit backfill is attempted because the required facts are not authoritative
there.

`GET /api/runs/{run_id}` is implemented as a thin HTTP adapter. The ownership
migration is additive and does not backfill historical rows; null-owner rows are
denied by default. Runtime supplies `user_id` through `ExecutionContext` and
`AgentRun`, and terminal projection persists it. The adapter only needs
`RunReader.get_run(run_id)` plus the shared access check; it must not read Trace
or Audit.
