# AgentLabKit

AgentLabKit 是一个用于构建、运行、观测和评估 AI agents 的 Python 与 React 平台。它包含可复用的 Agent Runtime、provider-neutral LLM gateway、RAG engine、guardrails、workflows、long-term memory、evaluation、cost analysis，以及 Web/desktop clients。

## Agent Engineering Loop

```text
Build Agent → Test → Run → Inspect / Replay → Capture → Evaluate → Compare → Improve
```

## Knowledge / RAG Journey

```text
Prepare Knowledge → Test Retrieval → Use in Agent → Test Agent → Inspect Retrieval → Diagnose
```

## Building applications on AgentLabKit

业务应用应把业务事实与权限留在自己的 Business Backend，通过 AgentLabKit 的 Platform API 使用 Agent、Knowledge、Tools、Runs 和 Evaluation。集成指南与当前支持范围见 [`docs/guides/building-business-applications.md`](docs/guides/building-business-applications.md)；公开 surface 的验证记录见 [`Business Integration Readiness Audit`](docs/guides/business-integration-readiness-audit.md)。

## 核心能力

- **Agent Runtime** — turn 与 streaming execution、tools、guardrails、handoffs、delegation 和 deterministic workflows。
- **Application use cases** — 执行、replay、将 Runs 加入 Dataset、评估 datasets，以及比较 evaluation runs。
- **LLM Gateway** — model catalog、provider adapters、routing/failover、credentials、retries、rate limiting 和 usage extraction。
- **Knowledge / RAG** — prepare and search knowledge；将 Knowledge 组合进 versioned Agents；观测真实 Runs 中的 retrieval；检查有界历史证据，并区分 no retrieval、zero results 和 failure；诊断 Retrieval 方向或 Agent 方向。
- **Platform services** — observability、cost analysis、evaluation 和 cross-session memory。
- **Clients** — FastAPI HTTP/SSE API、React administration console，以及 standalone PySide6 desktop client。

## 架构

仓库将以下边界视为稳定边界：Execution Model v2、Application Use Case v1 和 FastAPI Adapter v1。只有出于具体的正确性或产品需求才可修改。

```text
客户端
  ├── React 管理后台
  ├── PySide6 桌面端
  └── 其他客户端
          │
          ▼
FastAPI HTTP/SSE 适配层
          │
          ├── 平台动作 → Application Use Cases
          │                         ↓
          │                     Runtime / Evaluation / Dataset 能力
          ├── 资源 API → Module Services
          └── 投影 / 查询 API → Readers / Stores / Aggregators

Runtime 运行时
  ├── AgentRun
  └── RuntimeEvent
         ├── Observability → Trace 观测投影
         └── Cost Analysis → CostRecord 成本投影

AgentRun → Dataset → Evaluation → Compare / Improve
```

FastAPI backend 是传输与组合层。

平台动作委托给 `packages/application`；面向资源的 API 保留在所属 module services；读取/投影 API 直接使用 Readers、Stores 或 Aggregators。FastAPI 不拥有 Runtime execution facts、evaluation semantics 或平台级编排。

### Application Use Case v1：应用用例

当前稳定的平台用例目录：

- `ExecuteAgent`
- `ReplayRun`
- `CaptureRunAsDatasetExample`
- `EvaluateDataset`
- `CompareEvaluationRuns`

Application 负责平台动作编排，但不拥有 Runtime facts、HTTP DTO、持久化 schema 或 evaluator semantics。Application contracts 不是 HTTP DTOs；资源 CRUD 仍由 module services 负责。

### Execution mental model：执行心智模型

```text
Runtime 产生事实
Event 描述事实
Run 界定一次执行
Trace 观测执行
Evaluation / Cost / Replay 消费事实
```

`Run != Trace`。`run_id != DatasetExample.example_id`。Replay 会创建一次新的 Runtime execution。Runtime 拥有 execution facts 与 identity；Trace 是真实 Run 的 Observability projection。Replay 和 Evaluation 通过 `RunExecutor` 请求真实 Runtime execution，不制造 Runs 或 execution IDs。

参见 [`docs/architecture/execution-model-v2.md`](docs/architecture/execution-model-v2.md)、[`docs/architecture/fastapi-adapter-boundary.md`](docs/architecture/fastapi-adapter-boundary.md) 和 [`docs/architecture/agent-turn-streaming.md`](docs/architecture/agent-turn-streaming.md) 中的权威长篇规则。

## 快速开始

### Docker（推荐）

要求：Docker 和 Docker Compose v2。

```bash
git clone https://github.com/hhtttttiger/AgentLabKit.git
cd AgentLabKit
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
  -e ../packages/memory -e "../packages/evaluation[ragas]" \
  -e ../packages/llm_gateway -e ../packages/agent_runtime \
  -e ../packages/application -e ".[dev]"
PYTHONPATH=src alembic upgrade head
PYTHONPATH=src python -m bootstrap
PYTHONPATH=src uvicorn main:create_app --factory --reload
```

数据库 migration 已重置为当前 schema baseline：旧 baseline 创建的数据库不支持升级，必须先备份/导出后重建数据库。开发环境可使用 `make reset`，然后重新执行上述 migration 与 bootstrap。详见 [`docs/operations/database-migrations.md`](docs/operations/database-migrations.md)。本地 backend 使用 Docker 暴露的 PostgreSQL `localhost:15432`，请据此配置 `.env`。

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
  application/       framework-neutral platform use cases / orchestration
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
- [`PRODUCT.md`](PRODUCT.md) — product purpose, journeys and UX principles。
- [`packages/application/README.md`](packages/application/README.md) — application use-case package boundary。
- [`docs/architecture/`](docs/architecture/) — Execution Model、FastAPI adapter 和 streaming contracts：[`execution-model-v2.md`](docs/architecture/execution-model-v2.md)、[`fastapi-adapter-boundary.md`](docs/architecture/fastapi-adapter-boundary.md)、[`agent-turn-streaming.md`](docs/architecture/agent-turn-streaming.md)。
- [`docs/operations/`](docs/operations/) — 本地与 Docker 开发操作。
- [`.env.example`](.env.example) — environment configuration template。

## 许可证

MIT
