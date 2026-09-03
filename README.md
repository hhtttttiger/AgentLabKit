# AgentLabKit

AgentLabKit 是一个用于构建、运行、观测和评估 AI agents 的 Python 与 React 平台。它包含可复用的 Agent Runtime、provider-neutral LLM gateway、RAG engine、guardrails、workflows、long-term memory、evaluation、cost analysis，以及 Web/desktop clients。

## 核心能力

- **Agent Runtime** — turn 与 streaming execution、tools、guardrails、handoffs、delegation 和 deterministic workflows。
- **Application use cases** — 执行、replay、将 Runs capture 为 DatasetExamples、评估 datasets，以及比较 evaluation runs。
- **LLM Gateway** — model catalog、provider adapters、routing/failover、credentials、retries、rate limiting 和 usage extraction。
- **Retrieval** — document processing、chunking、embeddings、vector/full-text/hybrid search，以及可选的 GraphRAG。
- **Platform services** — observability、cost analysis、evaluation 和 cross-session memory。
- **Clients** — FastAPI HTTP/SSE API、React administration console，以及 standalone PySide6 desktop client。

## 架构

仓库将以下边界视为稳定边界：Execution Model v2、Application Use Case v1 和 FastAPI Adapter v1。只有出于具体的正确性或产品需求才可修改。

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

FastAPI 负责验证 HTTP、认证与授权、映射 DTO、委托调用，以及适配 HTTP/SSE。平台 orchestration 属于 `packages/application`；resource CRUD 属于 module services；query endpoints 使用 readers、stores 或 projections。

Runtime 拥有 execution facts 与 identity。`Run` 不是 `Trace`：Trace 是真实 Run 的 Observability projection。Replay 和 Evaluation 通过 `RunExecutor` 请求真实 Runtime execution；它们不会制造 Runs 或 execution IDs。Dataset storage 拥有稳定的 `example_id`；它永远不是 `run_id`。

参见 [`docs/architecture/execution-model-v2.md`](docs/architecture/execution-model-v2.md) 和 [`docs/architecture/fastapi-adapter-boundary.md`](docs/architecture/fastapi-adapter-boundary.md) 中的权威长篇规则。

## 快速开始

### Docker（推荐）

要求：Docker 和 Docker Compose v2。

```bash
git clone https://github.com/your-org/agentlabkit.git
cd agentlabkit
cp .env.example .env
docker compose up --build
```

- Admin console：<http://localhost:3000/admin/>
- API health：<http://localhost:8000/health>
- 默认账号：`admin` / `admin`

### 本地开发

先用 Docker 启动 PostgreSQL 和 Redis，再安装 backend packages，并分别运行 API、worker 和 frontend：

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

在另一个终端运行 indexing worker：

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=src python -m worker
```

在第三个终端运行 admin console：

```bash
cd frontend/admin
npm install
npm run dev
```

基础设施和故障排查详情见 [`docs/operations/local-debug.md`](docs/operations/local-debug.md) 和 [`docs/operations/docker-debug.md`](docs/operations/docker-debug.md)。

### Desktop client

Desktop client 使用 local SQLite 和 package APIs，不依赖 backend：

```bash
pip install PySide6
pip install -e packages/llm_gateway -e packages/agent_runtime
cd desktop
python main.py
```

Desktop 配置保存在 `~/.config/agentlabkit/desktop.toml`。参见 [`docs/desktop-app-plan.md`](docs/desktop-app-plan.md)。

## 仓库布局

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

## 开发

- Python packages 使用 `pytest`；从仓库根目录运行 targeted tests，例如 `python3 -m pytest packages/evaluation/tests/`。
- Admin frontend 在 `frontend/admin` 使用 `npm run check`、`npm run test` 和 `npm run build`。
- 将 LLM provider calls 保持在 `llm_gateway` 内，将 RAG processing 保持在 `retrieval` 内。
- 将 public HTTP/SSE contracts 保持在 adapter/module boundary；不要意外暴露 Runtime internals。

## 文档

- [`AGENTS.md`](AGENTS.md) — 简明的仓库级 coding constraints。
- [`packages/application/README.md`](packages/application/README.md) — application use-case package boundary。
- [`docs/architecture/`](docs/architecture/) — Execution Model、FastAPI adapter 和 streaming contracts。
- [`docs/operations/`](docs/operations/) — 本地与 Docker 开发操作。
- [`.env.example`](.env.example) — environment configuration template。

## 许可证

MIT
