# 本地调试指南

基础设施用 Docker，后端和前端在本地运行，改代码即时生效，不需要 rebuild 镜像。

## 架构

```
┌─────────────┐     ┌─────────────────────┐
│  Frontend    │     │  Backend (Web)       │
│  Vite :5173  │────▶│  Uvicorn :8000       │
│  本地 npm    │     │  (生产者: enqueue)    │
└─────────────┘     └──────────┬──────────┘
                               │ Redis Streams
                    ┌──────────▼──────────┐
                    │  Worker (独立进程)     │
                    │  (消费者: 索引 pipeline)│
                    └──────────┬──────────┘
                               │
                        ┌──────▼──────┐
                        │   Docker    │
                        ├─────────────┤
                        │ PostgreSQL  │ :5432
                        │ Redis       │ :6379
                        └─────────────┘
```

## 前置条件

- Python >= 3.12
- Node.js >= 22
- Docker + Colima（macOS ARM）

## 1. 启动基础设施

```bash
docker compose up -d postgres redis
```

验证：

```bash
docker compose ps
# postgres   healthy   0.0.0.0:5432->5432/tcp
# redis      healthy   0.0.0.0:6379->6379/tcp
```

## 2. 启动后端

### 2.1 安装依赖

```bash
cd backend

# 创建虚拟环境（首次）
python3 -m venv .venv
source .venv/bin/activate

# 安装本地包（按依赖顺序）
pip install -e ../packages/db
pip install -e ../packages/infra
pip install -e ../packages/retrieval
pip install -e ../packages/cost_analysis
pip install -e ../packages/observability
pip install -e ../packages/memory
pip install -e ../packages/evaluation
pip install -e ../packages/llm_gateway
pip install -e ../packages/agent_runtime

# 安装后端本身（含所有 PyPI 依赖）
pip install -e ".[dev]"
```

### 2.2 数据库迁移

```bash
cd backend
PYTHONPATH=src:../packages/llm_gateway/src:../packages/agent_runtime/src alembic upgrade head
```

### 2.3 初始化种子数据

```bash
PYTHONPATH=src:../packages/llm_gateway/src:../packages/agent_runtime/src python -m bootstrap
```

### 2.4 启动服务

```bash
cd backend
PYTHONPATH=src:../packages/llm_gateway/src:../packages/agent_runtime/src uvicorn main:create_app --factory --host 0.0.0.0 --port 8000 --reload
```

`--reload` 会在代码变更时自动重启。

验证：

```bash
curl http://localhost:8000/health
# {"success":true,"msg":"ok","data":{"status":"healthy"}}
```

### 2.5 启动 Worker

后端只 enqueue 文档处理消息;独立 worker 进程消费队列,运行索引 pipeline(分块 + embedding + 向量存储)。没有 worker,新建的文档会一直停在 `Pending`。在另一个终端启动:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=src:../packages/llm_gateway/src:../packages/agent_runtime/src python -m worker
```

验证日志显示:

```
Consumer doc-worker-<host> started on document_processing (concurrency=3)
Worker ready, waiting for messages (Ctrl-C to stop)
```

### 环境变量

后端从 `.env` 文件读取配置（项目根目录），默认值已适配本地开发，一般不需要改。

关键变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `APP_DB_HOST` | `localhost` | Docker PostgreSQL 地址 |
| `APP_DB_PORT` | `5432` | PostgreSQL 端口 |
| `APP_DB_USER` | `app` | 数据库用户 |
| `APP_DB_PASSWORD` | `devpassword` | 数据库密码 |
| `APP_DB_NAME` | `agentlabkit` | 数据库名 |
| `APP_DEBUG` | `false` | 调试模式 |
| `APP_REDIS__ENABLED` | `true` | 队列开关(注意双下划线;web enqueue,worker 消费) |
| `APP_RETRIEVAL__ENABLED` | `true` | RAG 索引开关(注意双下划线;知识库文档索引) |

## 3. 启动前端

```bash
cd frontend/admin
npm install    # 首次或依赖变更后
npm run dev
```

Vite dev server 默认在 `http://localhost:5173`，API 请求自动代理到 `http://localhost:8000`（由 `.env.local` 中的 `VITE_API_PROXY_TARGET` 控制）。

验证：浏览器打开 `http://localhost:5173/`

> **注意**：本地开发模式路径是 `/`，不是 `/admin/`。`/admin/` 是 Docker 模式下 nginx 的路径。

默认账号：`admin / admin`

## 4. 常用命令速查

```bash
# ── 基础设施 ──
docker compose up -d postgres redis     # 启动
docker compose down                      # 停止
docker compose logs -f postgres          # 查看日志

# ── 后端 ──
cd backend && source .venv/bin/activate  # 激活虚拟环境
PYTHONPATH=src:../packages/llm_gateway/src:../packages/agent_runtime/src uvicorn main:create_app --factory --port 8000 --reload
PYTHONPATH=src:../packages/llm_gateway/src:../packages/agent_runtime/src alembic upgrade head      # 执行迁移
PYTHONPATH=src:../packages/llm_gateway/src:../packages/agent_runtime/src alembic revision --autogenerate -m "描述"  # 生成迁移

# ── Worker ──
make worker                              # 启动文档索引 worker（本地进程）
PYTHONPATH=src:../packages/llm_gateway/src:../packages/agent_runtime/src python -m worker  # 等价

# ── 前端 ──
cd frontend/admin
npm run dev                              # 启动 dev server
npm run check                            # TypeScript 类型检查
npm run lint                             # ESLint 检查
npm run test                             # 运行测试
```

## 5. 切换到全 Docker 模式

如果需要验证完整部署流程：

```bash
docker compose up --build    # 构建并启动所有服务(web + worker + postgres + redis)
# 前端: http://localhost:3000/admin/
# 后端: http://localhost:8000/health
# Worker: 独立容器,消费队列运行索引 pipeline(一镜像多角色,与 backend 共享镜像)
docker compose down           # 停止并清理
```
