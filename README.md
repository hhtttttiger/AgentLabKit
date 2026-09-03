# AgentLabKit

AgentLabKit is a Python and React platform for building, running, observing, and evaluating AI agents. It includes a reusable Agent Runtime, provider-neutral LLM gateway, RAG engine, guardrails, workflows, long-term memory, evaluation, cost analysis, and web/desktop clients.

## Core capabilities

- **Agent Runtime** — turn and streaming execution, tools, guardrails, handoffs, delegation, and deterministic workflows.
- **Application use cases** — execute, replay, capture Runs as DatasetExamples, evaluate datasets, and compare evaluation runs.
- **LLM Gateway** — model catalog, provider adapters, routing/failover, credentials, retries, rate limiting, and usage extraction.
- **Retrieval** — document processing, chunking, embeddings, vector/full-text/hybrid search, and optional GraphRAG.
- **Platform services** — observability, cost analysis, evaluation, and cross-session memory.
- **Clients** — FastAPI HTTP/SSE API, React administration console, and standalone PySide6 desktop client.

## Architecture

The repository treats these boundaries as stable: Execution Model v2, Application Use Case v1, and FastAPI Adapter v1. Change them only for a concrete correctness or product requirement.

```text
Web / Desktop / External Client
              │
              ▼
       FastAPI adapter
              │
       ┌──────┼────────┐
       ▼      ▼        ▼
 Application  Module   Projection /
 use cases   services  Readers / Stores
       │      │        │
       └──────┼────────┘
              ▼
 Domain packages and Agent Runtime
```

FastAPI validates HTTP, authenticates and authorizes, maps DTOs, delegates, and adapts HTTP/SSE. Platform orchestration belongs in `packages/application`; resource CRUD belongs in module services; query endpoints use readers, stores, or projections.

Runtime owns execution facts and identity. `Run` is not `Trace`: Trace is an observability projection of a real Run. Replay and Evaluation request real Runtime execution through `RunExecutor`; they do not manufacture Runs or execution IDs. Dataset storage owns stable `example_id`; it is never a `run_id`.

See [`docs/architecture/execution-model-v2.md`](docs/architecture/execution-model-v2.md) and [`docs/architecture/fastapi-adapter-boundary.md`](docs/architecture/fastapi-adapter-boundary.md) for the authoritative long-form rules.

## Quick start

### Docker (recommended)

Requirements: Docker and Docker Compose v2.

```bash
git clone https://github.com/your-org/agentlabkit.git
cd agentlabkit
cp .env.example .env
docker compose up --build
```

- Admin console: <http://localhost:3000/admin/>
- API health: <http://localhost:8000/health>
- Default account: `admin` / `admin`

### Local development

Start PostgreSQL and Redis with Docker, then install the backend packages and run the API, worker, and frontend separately:

```bash
make up

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ../packages/db -e ../packages/infra -e ../packages/retrieval \
  -e ../packages/cost_analysis -e ../packages/observability \
  -e ../packages/memory -e ../packages/evaluation \
  -e ../packages/llm_gateway -e ../packages/agent_runtime \
  -e ../packages/application -e ".[dev]"
PYTHONPATH=src alembic upgrade head
PYTHONPATH=src python -m bootstrap
PYTHONPATH=src uvicorn main:create_app --factory --reload
```

In another terminal, run the indexing worker:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=src python -m worker
```

Run the admin console in a third terminal:

```bash
cd frontend/admin
npm install
npm run dev
```

For infrastructure and troubleshooting details, see [`docs/operations/local-debug.md`](docs/operations/local-debug.md) and [`docs/operations/docker-debug.md`](docs/operations/docker-debug.md).

### Desktop client

The desktop client uses local SQLite and package APIs without the backend:

```bash
pip install PySide6
pip install -e packages/llm_gateway -e packages/agent_runtime
cd desktop
python main.py
```

Desktop configuration is stored at `~/.config/agentlabkit/desktop.toml`. See [`docs/desktop-app-plan.md`](docs/desktop-app-plan.md).

## Repository layout

```text
packages/
  application/       framework-neutral platform use cases
  agent_runtime/     execution, tools, guardrails, memory, workflows
  llm_gateway/      provider-neutral LLM access and model routing
  retrieval/        document and RAG engine
  evaluation/       DatasetExample and evaluator contracts
  observability/    RuntimeEvent → Trace projection
  cost_analysis/    usage → cost projection
  memory/           cross-session memory
  db/               shared ORM and Snowflake IDs
  infra/            Redis, cache, and queue primitives
backend/
  src/main.py        FastAPI app factory and composition root
  src/modules/       resource APIs and application adapters
  src/modules/runs/  Run reads, replay, and capture adapters
  src/worker.py      indexing worker
frontend/admin/      React administration console
 desktop/            standalone PySide6 client
docs/architecture/  authoritative architecture decisions
```

## Development

- Python packages use `pytest`; run targeted tests from the repository root, for example `python3 -m pytest packages/evaluation/tests/`.
- The admin frontend uses `npm run check`, `npm run test`, and `npm run build` from `frontend/admin`.
- Keep LLM provider calls inside `llm_gateway` and RAG processing inside `retrieval`.
- Keep public HTTP/SSE contracts in the adapter/module boundary; do not expose Runtime internals by accident.

## Documentation

- [`AGENTS.md`](AGENTS.md) — concise repository-wide coding constraints.
- [`packages/application/README.md`](packages/application/README.md) — application use-case package boundary.
- [`docs/architecture/`](docs/architecture/) — Execution Model, FastAPI adapter, and streaming contracts.
- [`docs/operations/`](docs/operations/) — local and Docker development operations.
- [`.env.example`](.env.example) — environment configuration template.

## License

MIT
