---
name: local-dev
description: "Start the AgentLabKit local development environment (Docker PostgreSQL/Redis + local backend/worker/frontend). Use when the user wants to run or debug the project locally."
trigger: /local-dev
---

# /local-dev

启动 AgentLabKit 的本地开发环境：Docker 基础设施 + 本地 FastAPI backend + 独立 worker + Vite admin frontend。

## Architecture

```
Vite frontend ──▶ FastAPI web (:8000) ──▶ PostgreSQL / Redis
                                      └──▶ Redis Streams ──▶ worker
```

- `backend/src/main.py` 是 FastAPI app factory。
- `backend/src/worker.py` 是通用 worker supervisor；默认会启用可用的
  `document_indexing` 和 trace ingestion tasks，不只是文档 worker。
- Web 进程只负责 enqueue；需要知识库索引时必须同时运行 worker。
- 本地模式中 backend、worker、frontend 在宿主机运行；PostgreSQL 和 Redis
  在 Docker 中运行。

## Prerequisites

- Python >= 3.12
- Node.js >= 22
- Docker Compose v2
- macOS 上通常还需要 Colima
- `make`

## 1. Prepare environment

首次使用时：

```bash
cp .env.example .env
```

本地 backend 连接 Docker 暴露的 PostgreSQL `localhost:15432`，Redis 使用
`localhost:6379`。确认 `.env` 至少包含与本地 Docker 对应的：

```dotenv
APP_DB_HOST=localhost
APP_DB_PORT=15432
APP_REDIS_URL=redis://localhost:6379/0
APP_REDIS_ENABLED=true
APP_RETRIEVAL_ENABLED=true
```

如果只调试不需要知识库索引，可以将 retrieval 关闭；此时不要启动或不要选择
document indexing task。

## 2. Start infrastructure

```bash
make up
make status
```

预期 `postgres` 和 `redis` 都是 healthy。数据保存在 Docker named volumes 中；
`make stop` 保留数据，`make reset` 会删除 PostgreSQL/Redis 数据卷。

### Existing database warning

最新 schema 使用 `backend/alembic/versions/0001_current_baseline.py`。
在该 baseline 之前创建的数据库不支持升级。遇到 migration incompatibility 时，
先备份需要保留的数据，再执行：

```bash
make reset
make up
```

不要修改 `alembic_version` 来绕过 baseline；详见
`docs/operations/database-migrations.md`。

## 3. Install backend packages

如果 `backend/.venv` 不存在，执行：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ../packages/db -e ../packages/infra -e ../packages/retrieval \
  -e ../packages/cost_analysis -e ../packages/observability \
  -e ../packages/memory -e ../packages/evaluation \
  -e ../packages/llm_gateway -e ../packages/agent_runtime \
  -e ../packages/application -e ".[dev]"
```

每个新终端都要先执行：

```bash
cd backend
source .venv/bin/activate
```

## 4. Migrate and bootstrap

在干净数据库或 migration 变更后执行：

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=src alembic upgrade head
PYTHONPATH=src python -m bootstrap
```

`bootstrap` 负责初始应用数据；schema 创建由 Alembic 负责。默认登录账号为
`admin / admin`（如 bootstrap 配置发生变化，以终端输出和当前代码为准）。

## 5. Start backend

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=src uvicorn main:create_app --factory \
  --host 0.0.0.0 --port 8000 --reload
```

验证：

```bash
curl -s http://localhost:8000/health
```

## 6. Start worker

在另一个终端执行：

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=src python -m worker
```

默认 `APP_WORKER_TASKS=*`，worker 会选择当前配置可用的 tasks。日志应出现
worker task started；如果启用了 retrieval 和 Redis，还应看到
`document_indexing`。没有 worker 时，新建知识库文档会停留在 Pending。

可通过 `APP_WORKER_TASKS` 选择任务，例如：

```dotenv
APP_WORKER_TASKS=document_indexing
```

## 7. Start frontend

首次或依赖变更后：

```bash
cd frontend/admin
npm install
```

确保 `frontend/admin/.env.local`（可由 `.env.example` 复制）将 API proxy 指向
本地 backend：

```bash
VITE_API_PROXY_TARGET=http://localhost:8000
```

启动：

```bash
cd frontend/admin
npm run dev
```

Vite 默认使用 5173；若端口被占用，以终端输出的实际端口为准。访问路径是
`/`，不是 Docker 模式的 `/admin/`。

## 8. Verify and report

| Service | URL / verification |
|---|---|
| Frontend | `http://localhost:<vite-port>/` |
| Backend | `http://localhost:8000/health` |
| Worker | terminal logs; no HTTP endpoint |
| PostgreSQL | `localhost:15432` |
| Redis | `localhost:6379` |

## Full Docker mode

需要验证完整容器部署时，不要启动本地 backend/frontend，执行：

```bash
docker compose up --build
```

此模式包含 `backend`、独立 `worker`、`postgres`、`redis` 和 nginx frontend：

- Admin console: `http://localhost:3000/admin/`
- API health: `http://localhost:8000/health`

停止：

```bash
docker compose down
```

## Lifecycle shortcuts

| Command | Effect |
|---|---|
| `make up` | 启动/恢复 PostgreSQL 和 Redis |
| `make stop` | 停止基础设施但保留数据 |
| `make reset` | 删除容器和数据卷；不可逆 |
| `make status` | 查看基础设施状态 |
| `make logs` | 查看 PostgreSQL/Redis 日志 |
| `make worker` | 使用当前 `.venv` 启动本地 worker |

不要把 `docker compose down -v` 当作普通停止命令；它会删除数据。
