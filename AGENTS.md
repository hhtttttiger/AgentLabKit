# AgentLabKit

## Scope

Repository-wide instructions. A nearer `AGENTS.md` may add local constraints for its subtree; it must not contradict these rules.

## Architecture invariants

- Runtime owns execution facts and identity (`run_id`, `trace_id`, spans, lifecycle events).
- `Run != Trace`: Trace is an observability projection of a real Run.
- Projectors, Replay, Evaluation, HTTP adapters, and the frontend must not invent execution facts or IDs.
- `run_id` is never a stable DatasetExample `example_id`.
- Application Use Case v1 is sealed: `ExecuteAgent`, `ReplayRun`, `CaptureRunAsDatasetExample`, `EvaluateDataset`, and `CompareEvaluationRuns`.
- FastAPI is an adapter, not the platform business layer. Platform actions delegate to Application Use Cases; resource APIs use Module Services; reads use Readers/Stores/Projections.
- `llm_gateway` is the only LLM API entrypoint. `retrieval` is the only document/embedding/vector-retrieval engine.
- Backend web indexing enqueues work; `backend/src/worker.py` consumes the queue.

These boundaries are stable. Change them only for a concrete correctness or product requirement and update the authoritative architecture reference.

## Repository map

- `packages/application` — framework-neutral platform use cases.
- `packages/agent_runtime` — Runtime, events, tools, guardrails, memory, and workflows.
- `packages/llm_gateway` / `packages/retrieval` — foundational LLM and RAG capabilities.
- `packages/evaluation`, `packages/observability`, `packages/cost_analysis`, `packages/memory` — platform projections and services.
- `packages/db` / `packages/infra` — shared database and infrastructure primitives.
- `backend` — FastAPI transport, composition root, module services, and worker.
- `frontend/admin` — React client of the public HTTP/SSE contract.
- `desktop` — standalone PySide6 client.
- `docs/architecture` — long-form architecture decisions.

## Change rules

- Keep routes thin and use the existing ownership boundary; do not add generic Controller, Facade, Manager, or command-bus layers.
- Do not change sealed contracts to preserve stale documentation. Update documentation to match source truth.
- Keep provider-specific integrations behind package protocols/adapters.
- Preserve explicit identity and ownership fields; never infer them from ordering, names, or fallback IDs.

## Verification

Use the nearest package guidance for targeted tests. For documentation-only changes, verify links and paths, search for stale architecture terms, and confirm every documented command/script exists. Frontend contract changes use `npm run check`, `npm run test`, and `npm run build` from `frontend/admin`.

## References

- [Execution Model v2](docs/architecture/execution-model-v2.md)
- [FastAPI adapter boundary](docs/architecture/fastapi-adapter-boundary.md)
- [Streaming contract](docs/architecture/agent-turn-streaming.md)
