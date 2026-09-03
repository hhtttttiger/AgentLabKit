# Public Execution API and Run Resource Audit

**Scope:** durable Run projection slice and the canonical public Run read adapter.
`GET /api/runs/{run_id}` is implemented; no frontend contract or application use case was changed.

**Sources inspected:** `backend/src/main.py`, the `ai_invoke`, `agent`, `observability`, `evaluation`, and `chat` modules, plus `packages/application`, `packages/agent_runtime`, `packages/observability`, and `packages/evaluation`. Source code, rather than historical plans, is authoritative for this report.

## Verdict

### A — BORING RUN READ API READY

`GET /api/runs/{run_id}` reads the durable `RunReader` projection directly. The
HTTP adapter does not invoke Runtime or consult Trace or AgentAudit.

The Runtime contract is sufficiently clear to define a public `Run` resource. A canonical `GET /api/runs/{run_id}` or `GET /api/runs` can now be implemented as a thin adapter over the authoritative durable Run read model.

`AgentRun` exists in Runtime memory and is returned by `AgentRuntime.run()`. The durable stores currently available are projections with different ownership:

- `trace_records` is a Trace/observability projection and intentionally does not contain the complete Run payload (`input`, `output`, Run-level error, action, tool names, metadata, etc.).
- `agent_execution_audits` is an agent-specific, best-effort audit/request summary written by the streaming adapter. It is not written by the current `POST /api/ai/invoke/agents/{agent_key}/turn` path and is not a complete Runtime Run projection.
- `eval_runs` is an evaluation orchestration record, not an `AgentRun`; its numeric `id` belongs to the EvaluationRun namespace.

Therefore, reconstructing a public Run from Trace or treating an audit row as a Run would violate the v2 ownership model. The next implementation step is a durable Run projection/read model fed by Runtime facts, not a new endpoint over an existing unrelated table.

## Current public execution-related surfaces

| Endpoint | Current meaning | Primary ID | Real resource |
|---|---|---|---|
| `POST /api/ai/invoke/agents/{agent_key}/turn` | Execute one agent turn and return a result envelope | Runtime `runId` and `traceId` in response | Runtime `AgentRun` result, exposed through a legacy invoke facade |
| `POST /api/ai/invoke/agents/{agent_key}/turn/stream` | Execute one agent turn over SSE | `runId`, `traceId` on mapped SSE events | Runtime `AgentRun` lifecycle, exposed through a legacy streaming facade |
| `GET /api/agents/{agent_key}/audits` | Paginated agent-specific execution audit summaries | Audit row `id`; each item also has `runId` | `AgentExecutionAudit`, not a general Run resource |
| `GET /api/agents/{agent_key}/audits/{run_id}` | Read one audit summary scoped to an agent key | `run_id` path plus `agent_key` | `AgentExecutionAudit`, compatibility/audit surface |
| `GET /api/traces` | Cursor-paginated observability records | `trace_id` | Trace projection (`TraceRecord`) |
| `GET /api/traces/{trace_id}` | Trace summary and all spans | `trace_id` | Trace plus `Span` projection |
| `GET /api/traces/stats` | Aggregate observability statistics | none | Trace statistics |
| `POST /api/eval/run-configs/{config_id}/run` | Start an evaluation orchestration job | EvaluationRun numeric `id` | `EvaluationRun` |
| `GET /api/eval/runs` | List evaluation orchestration runs | EvaluationRun numeric `id` | `EvaluationRun`, not AgentRun |
| `GET /api/eval/runs/{run_id}` | Get an evaluation run and its per-case results | EvaluationRun numeric `id` | `EvaluationRun` plus `EvaluationRunResult` |
| `GET /api/chat/sessions` | List chat sessions | Chat session numeric `id` | `ChatSession` |
| `GET /api/chat/sessions/{session_id}/messages` | Read messages in a session | Chat session numeric `id` | `ChatMessage` collection |
| `POST /api/chat/sessions/{session_id}/messages/save-turn` | Persist a chat turn in a session | Session id and message ids | Chat persistence; not execution identity |

The `GET /api/eval/runs*` names are a compatibility hazard: they use `run` terminology for `EvaluationRun`, but must not be aliased to public AgentRun endpoints without an explicit namespace/resource distinction.

### Existing ExecuteAgent transport contract

`POST /api/ai/invoke/agents/{agent_key}/turn` accepts `Message`, optional `SessionId`, optional `UserId`, and `History`. Its response currently exposes `runId`, `traceId`, `sessionId`, `action`, `replyText`, target information, usage, and error, but does not expose the Runtime `status`, timestamps, duration, metadata, or tool records (the HTTP `toolEvents` value is currently empty). The non-streaming path is therefore a compatible execution facade, not a complete Run representation.

The streaming endpoint preserves SSE framing and emits mapped facade events (`context`, `reply_delta`, `tool_call`, `tool_result`, `handoff`, `completed`, and `error`), followed by `[DONE]`. The adapter injects Runtime-owned `runId`/`traceId` into events. Its facade terminal fields use `status: "succeeded"` for `completed`/`handoff` and `status: "failed"` for `error`; these are transport values and should not replace the canonical Runtime statuses (`completed`, `failed`, `cancelled`). A client disconnect/cancellation is not currently exposed as a durable Run query result through this endpoint.

One additional compatibility debt was found in `backend/src/modules/ai_invoke/agent_turn.py`: the unused/legacy `run_agent_turn_stream` helper initializes `run_id` and `trace_id` to empty strings and does not copy them from the runtime events before mapping or auditing. The production router uses `ExecuteAgent`/`run_execute_agent_stream`, so this was not changed in the audit; it must be corrected or retired before that helper is exposed again.

## Identity map and invariants

| Identity | Owner | Meaning | Relationship |
|---|---|---|---|
| `run_id` | Runtime / `ExecutionContext` | One real execution boundary | Created by Runtime; unique from `trace_id` |
| `trace_id` | Runtime, observed by Observability | Observability projection key | One Trace is linked to the Run by `trace_id` |
| `root_span_id` / `span_id` | Runtime | Span identity and hierarchy | Belongs to Trace detail, not a Run API payload |
| `session_id` | Chat/session context and Runtime request context | Conversation grouping/context | One Session can contain many Runs; Session != Run |
| EvaluationRun `id` | Evaluation module/database | Evaluation orchestration lifecycle | One EvaluationRun can produce many real AgentRuns |
| `AgentExecutionAudit.id` | Agent backend persistence | Database identity of an agent audit row | Not a Run identity; its `run_id` is a reference copied from Runtime when available |
| `DatasetExample.example_id` | Dataset/evaluation contracts | Stable example identity | Never equal to `run_id`; source Run ids are provenance only |

The Runtime code uses the supplied `ExecutionContext` for `run_id`, `trace_id`, and root span identity. `AgentRuntime.run()` returns an `AgentRun`, and the lifecycle events carry both `run_id` and `trace_id`. The code paths audited do not use `trace_id` as `run_id` or fall back from one to the other. The trace store persists both separately (including a UUID cast for `run_id`) and the projector keeps a separate `run_id -> trace_id` mapping.

## Runtime Run semantics

The authoritative `AgentRun` fields are:

- identity: `run_id`, optional `trace_id`;
- lifecycle: `status`, `started_at`, `finished_at`, and computed `duration_ms`;
- execution: `input`, `output`, `target`, `session_id`, and `metadata`;
- outcome detail: `error`, `action`, handoff target and orchestration chain;
- summaries: usage, tool names/count, and applied skills.

The public resource should expose a deliberately smaller, framework-neutral subset. It should communicate what execution occurred and how it ended, not reproduce Runtime internals or the Trace tree.

### Status and outcome

The Runtime-defined status set is:

- `running`
- `completed`
- `failed`
- `cancelled`

Guardrail blocking is explicitly a valid business outcome. The input guard path emits `GuardrailBlocked` and then `RunCompleted` with `attributes: {"outcome": "blocked", "blocked": true}`. A future public representation should preserve this distinction, for example `status: "completed"` plus `outcome: "blocked"`; it must not convert it to `failed` merely because no model response was produced.

Handoff and delegation are execution semantics/summary fields, not additional terminal statuses. `paused`/`checkpointed` are not present in the current Run status contract. Resume must wait for a real workflow checkpoint capability and its actual identity model.

## Proposed public boundary (not implemented)

Recommended terminology:

- **Execution** is the platform action/process concept.
- **Run** is the durable/public record of one execution boundary.
- Use `Run` in the public API; do not introduce parallel names such as `ExecutionRecord` or `InvocationRun`.

A future `RunSummary` should contain only fields available from the durable projection, likely:

```text
runId, traceId, status, outcome,
target summary, startedAt, completedAt, durationMs,
sessionId/user relation when authorized,
usage summary, tool summary, error summary, metadata/related links
```

A future `RunDetail` may add input/output and related identifiers, subject to privacy and payload policy. Missing facts remain null/omitted; they must not be synthesized from database timestamps, Trace data, or fallback IDs. Neither summary nor detail should contain full spans, the event timeline, retrieval chunks, every tool span, or LLM internals. Those remain under Trace/Observability APIs.

## Capability classification

| Public capability | Canonical resource | Application UC | Backend direct/query | Status |
|---|---|---|---|---|
| Execute Agent | Run | `ExecuteAgent` | — | Existing via `/api/ai/invoke`; compatibility facade |
| Get Run | Run | — | `RunReader` / durable Run read model | Implemented: `GET /api/runs/{run_id}` |
| List Runs | Run | — | Not in current `RunReader` contract | Deferred until list contract is defined |
| Get Trace | Trace | — | `TraceStore` | Existing |
| List Traces | Trace | — | `TraceStore` | Existing |
| Execute Dataset Evaluation | EvaluationRun + AgentRuns | `EvaluateDataset` | Evaluation adapter/store | Existing for agent target |
| Replay Run | new Run linked to source Run | `ReplayRun` | — | Application scaffold; production wiring forbidden this round |
| Capture Run as Dataset Example | DatasetExample | `SaveRunAsDatasetExample` | — | Application scaffold; production wiring forbidden this round |
| Cancel Run | Run | Future capability, likely UC | Runtime cancellation/active registry | Deferred; HTTP reliability not established |
| Resume | Workflow/checkpoint (not assumed Run) | Future UC | Workflow runtime | Deferred; current identity/capability not established |
| Compare Evaluation Runs | Evaluation comparison | `CompareEvaluationRuns` (future) | Evaluation | Deferred |

Resource CRUD for agents, datasets, examples, budgets, chats, and memories remains outside the Application layer. Knowledge ingestion/reindexing is a separate follow-up audit.

## Replay and capture design direction

Replay should be source-Run oriented (`POST /runs/{run_id}/replay` is a candidate), but it must call Runtime through `ReplayRun`/`RunExecutor`. The client may provide only supported overrides and metadata; it may never submit `run_id` or `trace_id`. Runtime creates both identities for the new execution, and the source id is provenance metadata.

Capture should preserve ownership boundaries: the source is a Run, the destination is a Dataset, and Dataset creates `example_id`. Candidate shapes include a Dataset-owned action (`POST /datasets/{dataset_id}/examples:from-run`) or a Run action (`POST /runs/{run_id}/capture`), but neither may equate `example_id` with `run_id`.

## Cancel and resume audit

The Runtime has a cancellation token and emits `RunCancelled` when an execution receives `asyncio.CancelledError`. This proves local execution semantics, but not a platform-level `cancel(run_id)` capability: the audit found no durable active-execution registry or HTTP command path that reliably locates and cancels an active process by public `run_id`. `CancelRun` is therefore deferred.

No current public/domain checkpoint contract was found that establishes whether resume is keyed by `run_id`, checkpoint id, workflow instance id, or session. `ResumeExecution` is deferred rather than prematurely designed as `POST /runs/{run_id}/resume`.

## Compatibility and migration strategy

1. Keep `/api/ai/invoke/agents/{agent_key}/turn` and `/stream` unchanged. Preserve request, response, SSE framing, and current `runId`/`traceId` fields.
2. Add a durable Runtime-event-fed Run projection/read model first, with explicit retention, authorization, privacy, and idempotency rules.
3. Add canonical Run reads/actions only after that store is authoritative. Prefer `/api/runs` over `/api/agent-runs` because Runtime targets already include agents, workflows, and evaluation targets.
4. Gradually migrate frontend reads/actions to the canonical surface. Existing invoke routes remain compatibility aliases/facades; no deprecation is proposed in this audit.
5. Keep `/api/traces` independent: `GET Run` is an execution summary and `GET Trace` is diagnostic detail. Run projection is durably stored in `run_records` and is not reconstructed from Trace.
6. Keep `/api/eval/runs` explicitly in the EvaluationRun namespace; do not overload it with AgentRun.

Intentional breaking changes: **none**.

## Implemented Run read adapter

`GET /api/runs/{run_id}` is the canonical AgentRun resource endpoint. It is an
authenticated, single-row read over `RunReader.get_run(run_id)`, mapped to the
public `RunResponse` DTO. The endpoint returns 404 when the durable Run does
not exist. `traceId` is only the stored association; Trace and AgentAudit are
not queried, and no status or timestamp is reconstructed.

The current Run projection does not carry sufficient ownership data for
resource-level authorization. Until an ownership model is established, the
endpoint follows the backend's existing coarse-grained rule: any authenticated
user may read a Run. This limitation is intentional and must be resolved before
exposing broader payloads or user-scoped listing.

## Next design step

Implement resource-level ownership authorization once the authoritative
ownership model is clarified. Do not infer it from Trace or AgentAudit.

## Deferred work

- production wiring for `ReplayRun`;
- production wiring for `SaveRunAsDatasetExample`;
- `CompareEvaluationRuns`;
- `CancelRun`;
- `ResumeExecution`;
- RAG/knowledge ingestion and reindexing audit;
- frontend migration to canonical Run reads/actions.
