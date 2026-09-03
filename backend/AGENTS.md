# Backend

## Role

`backend` is the FastAPI transport and composition layer. It exposes the public HTTP/SSE contract, wires package capabilities, owns module resource services, and runs the indexing worker. It is not the platform orchestration layer.

## Endpoint ownership

- **Platform action → Application Use Case**: agent turn/replay/capture and agent-target evaluation/compare.
- **Resource API → Module Service**: authentication, agents, model catalog, knowledge bases, chat, files, glossary, memories, datasets, budgets, and definitions.
- **Projection/query → Reader, Store, or aggregator**: Runs, traces, costs, model usage, and evaluation-run reads.

Use the existing boundary in [`docs/architecture/fastapi-adapter-boundary.md`](../docs/architecture/fastapi-adapter-boundary.md). The `runs` module is the HTTP adapter for Run reads, replay, and capture; it does not own Runtime identity.

## Rules

- Keep routes thin: validate HTTP input, authenticate/authorize, map DTOs, delegate, and adapt the result to HTTP or SSE.
- Do not construct `AgentRun`, generate execution IDs, calculate evaluation verdicts, or reconstruct Trace from Run data in routes/services.
- Keep application orchestration in `packages/application`; keep CRUD/resource behavior in the owning module service.
- Preserve the public envelope and SSE contract; internal `RuntimeEvent` values are not automatically public API.
- Web indexing only enqueues work. `src/worker.py` consumes it in a separate process.

## Key paths

- `src/main.py` — app factory, lifespan, composition root, router registration.
- `src/runtime/` — package adapters and application wiring.
- `src/modules/` — HTTP modules and resource services.
- `src/modules/runs/` — Run reader and Application Use Case adapters.
- `alembic/` — database migrations.

## Verification

From `backend/`, run targeted tests for the changed module. For runtime/application boundary changes, also run the relevant package tests under `packages/*/tests`. Validate imports with `PYTHONPATH=src` when invoking backend modules.

## References

- [Root instructions](../AGENTS.md)
- [FastAPI adapter boundary](../docs/architecture/fastapi-adapter-boundary.md)
- [Execution Model v2](../docs/architecture/execution-model-v2.md)
