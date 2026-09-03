# FastAPI adapter boundary

Application Use Case v1 is a stable boundary.

Current core:

- `ExecuteAgent`
- `ReplayRun`
- `CaptureRunAsDatasetExample`
- `EvaluateDataset`
- `CompareEvaluationRuns`

New use cases require an explicit promotion decision. FastAPI refactoring must not
redesign these contracts unless a correctness bug is found.

## Boundary

FastAPI is the public HTTP adapter. A route parses HTTP, applies authentication and
resource authorization, maps DTOs, delegates once, and maps the result to HTTP.
There is no controller, facade, command bus, or generic response framework.

### Platform actions

| Endpoint | Owner |
|---|---|
| `POST /api/ai/invoke/agents/{agent_key}/turn` | `ExecuteAgent` |
| `POST /api/ai/invoke/agents/{agent_key}/turn/stream` | `ExecuteAgent` + SSE adapter |
| `POST /api/runs/{run_id}/replay` | `ReplayRun` |
| `POST /api/runs/{run_id}/capture` | `CaptureRunAsDatasetExample` |
| `POST /api/eval/run-configs/{config_id}/run` (agent target) | `EvaluateDataset` |
| `POST /api/eval/runs/compare` | `CompareEvaluationRuns` |

The evaluation `rag_pipeline` target remains on its existing legacy runner until
its target contract is explicitly promoted. Evaluation-run ownership currently has
no persisted owner/project fact; compare therefore uses the existing authenticated
evaluation API boundary and does not infer ownership from Dataset, Run, or Trace.
This is an explicit authorization limitation, not a new ownership model.

### Resource APIs

These remain module-owned: agent and agent-version CRUD, dataset and DatasetExample
CRUD, chat sessions, memories, files, glossary, knowledge bases/documents, budgets
and alerts, LLM catalog, tool/skill/MCP definitions, and legacy RAG evaluation.
Routes delegate to their existing module services.

### Projection / query APIs

These remain direct read paths: `GET /api/runs/{run_id}` via `RunReader`, trace
list/detail/stats via `TraceStore`, cost overview/breakdowns/trend via the cost
aggregator, model usage queries, and evaluation-run list/detail via the existing
read service. They are not wrapped in new Get* use cases.

## Public route inventory

| Method/path | Module | Owner / classification | Action |
|---|---|---|---|
| `POST /api/auth/login` | auth | auth service / Resource | keep |
| `/api/agents/**` | agent | `AgentService` / Resource | keep |
| `/api/agent-tools/**`, `/api/agent-skills/**`, `/api/agent-mcp/**` | agent | module services / Resource | keep |
| `/api/knowledge-bases/**` | knowledge_base | KB, Document, Search services / Resource | defer promotion; worker enqueue remains |
| `/api/chat/**` | chat | `ChatService` / Resource | keep |
| `POST /api/ai/invoke/agents/*/turn[\/stream]` | ai_invoke | `ExecuteAgent` / Platform Action | thin adapter; preserve SSE |
| `POST /api/ai/invoke/{model_id}/text[\/stream]`, embedding test | ai_invoke | `InvokeService` / Resource-like gateway action | keep legacy contract |
| `/api/files/**` | files | `FileService` / Resource | keep |
| `/api/glossary/**` | glossary | `GlossaryService` / Resource | keep |
| `/api/cost/overview`, breakdown, trend | cost | aggregator / Projection | keep direct |
| `/api/cost/budgets/**` | cost | `BudgetService` / Resource | keep |
| `/api/cost/alerts/**` | cost | budget manager / Resource action | keep |
| `/api/traces/**` | observability | `TraceStore` / Projection | keep direct |
| `/api/memories/**` | memory | memory module / Resource | keep |
| `/api/eval/datasets/**` | evaluation | `DatasetService` / Resource | keep |
| `/api/eval/run-configs` | evaluation | `RunService` / Resource | keep |
| `POST /api/eval/run-configs/*/run` | evaluation | `EvaluateDataset` for agents; legacy RAG otherwise | thin scheduling adapter; legacy deferred |
| `/api/eval/runs` | evaluation | `RunService` / Projection | keep |
| `POST /api/eval/runs/compare` | evaluation | `CompareEvaluationRuns` / Platform Action | delegate once |
| `/api/model-usage/**` | model_usage | usage service / Projection | keep direct |
| `GET /api/runs/{run_id}` | runs | `RunReader` / Projection | keep direct |
| `POST /api/runs/{run_id}/replay` | runs | `ReplayRun` / Platform Action | delegate once |
| `POST /api/runs/{run_id}/capture` | runs | `CaptureRunAsDatasetExample` / Platform Action | delegate once |

Capture HTTP transport artifacts (dependency and DTOs) belong to the `runs`
module because the resource endpoint is exposed there. Capture returns `datasetId`,
`sourceRunId`, and `exampleId`. Source Run access is checked before delegation;
missing/inaccessible Runs return 404 and non-completed Runs return 409. Dataset
existence is enforced by the existing Dataset service.

The execution SSE contract is unchanged: the adapter still emits public SSE
`type`, `data`, `runId`, terminal semantics, and `[DONE]`; internal
`RuntimeEvent` values are not exposed directly. `RunResponse` is unchanged.
