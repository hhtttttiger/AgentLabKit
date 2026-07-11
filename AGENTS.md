# AGENTS.md — AgentLabKit

AI Agent 平台。Python + React 全栈。

## 架构原则

### 底层能力层

系统中两个**底层能力包**，业务模块需要这些能力时必须依赖它们：

| 能力包 | 位置 | 职责 |
|--------|------|------|
| **`llm_gateway`** | `packages/llm_gateway/` | LLM 统一访问、路由、负载均衡、凭据解析、Usage 提取 |
| **`retrieval`** | `packages/retrieval/` | RAG 引擎：文档处理、分块、Embedding、向量检索 |

**关键约束：**
- `llm_gateway` 是系统**唯一**调用 LLM API 的入口
- `retrieval` 是系统**唯一**处理文档/Embedding/向量检索的引擎
- 业务模块通过**适配器**（如 `KnowledgeRetrievalService`、`GatewayEmbeddingProvider`）桥接

### 基础设施层

**`infra`** (`packages/infra/`) 不依赖任何项目模块，提供 Redis 连接管理、缓存、消息队列。

### 依赖方向

```
┌──────────────────────────────────────────────────────────────┐
│                            应用层                              │
│   backend (业务模块 + HTTP)      ·      frontend (admin)      │
└──────┬───────────────────────────────────────────┬───────────┘
       │                                           │
       ▼                                           ▼
┌──────────────────────┐                ┌────────────────────────────┐
│    Agent 编排层        │  ◀── 可选挂载 ── │       平台能力层             │
│    agent_runtime     │   (memory /     │  cost_analysis             │
│  (run_turn / 工具 /   │   observability)│  evaluation               │
│   guardrails / 短期   │                 │  memory · observability    │
│   memory)            │                 │  (成本/评估/长期记忆/链路追踪) │
└──────────┬───────────┘                └─────────────┬──────────────┘
           │                                          │
           └────────────────────┬─────────────────────┘
                                ▼
            ┌──────────────────────────────────────────┐
            │              底层能力层                     │
            │   llm_gateway  ·  retrieval               │
            │   (模型路由/调用  ·  RAG 文档处理/检索)       │
            └────────────────────┬─────────────────────┘
                                 ▼
            ┌──────────────────────────────────────────┐
            │  packages/db (ORM · Engine · Snowflake ID) │
            └────────────────────┬─────────────────────┘
                                 ▼
            ┌──────────────────────────────────────────┐
            │  packages/infra (Redis · Cache · 队列)     │
            └──────────────────────────────────────────┘
```

**文档索引拆分为独立进程：** web 只 enqueue（生产者），`backend/src/worker.py` 消费队列（消费者），通过 Redis Streams 解耦。详见 `independent-indexing-worker` memory。

**两个 memory 不要混淆：** `agent_runtime/memory` 是**单会话** Token-aware 上下文裁剪；`packages/memory` 是**跨会话**长期记忆（pgvector）。后者通过 `MemoryInjector` 注入前者管理的消息列表。详见各包 AGENTS.md。

## 技术栈

- **Backend**: Python 3.12, FastAPI, SQLAlchemy (async), asyncpg, PostgreSQL 16 + pgvector
- **Cache/Queue**: Redis 7 (async, hiredis), Redis Streams — 文档索引 worker 独立消费(`backend/src/worker.py`)
- **Frontend**: React 19, TypeScript, Vite, Zustand, React Query
- **Auth**: JWT (HS256), bcrypt

## 本地启动

```bash
docker compose up --build
```

| 服务 | 地址 |
|------|------|
| Frontend | http://localhost:3000/admin/ |
| Backend API | http://localhost:8000/health |
| Worker | 独立进程,无 HTTP (`make worker` / `python -m worker`) |
| PostgreSQL | localhost:5432 (app / <DB_PASSWORD> / agentlabkit) |
| Redis | localhost:6379 |

默认账号：`admin / admin`。API 统一 envelope: `{ "success": bool, "msg": string, "data": T }`

---

## 快速定位（按任务找模块）

| 我要做的 | 去这里 |
|---------|--------|
| 改 LLM 调用 / 模型路由 / 凭据解析 | [`packages/llm_gateway`](packages/llm_gateway/AGENTS.md) |
| 改 RAG / 文档分块 / Embedding / 向量检索 | [`packages/retrieval`](packages/retrieval/AGENTS.md) |
| 改 Agent 执行循环 / 动态工具 / Guardrails | [`packages/agent_runtime`](packages/agent_runtime/AGENTS.md) |
| 单会话上下文裁剪（Token / 摘要） | [`agent_runtime/memory`](packages/agent_runtime/src/agent_runtime/memory/AGENTS.md) |
| 跨会话长期记忆（pgvector） | [`packages/memory`](packages/memory/AGENTS.md) |
| 成本统计 / 预算 / 告警 | [`packages/cost_analysis`](packages/cost_analysis/AGENTS.md) |
| 评估 / LLM-as-Judge / 指标 | [`packages/evaluation`](packages/evaluation/AGENTS.md) |
| 链路追踪 / Span / Trace | [`packages/observability`](packages/observability/AGENTS.md) |
| Redis / 缓存 / 消息队列 | [`packages/infra`](packages/infra/AGENTS.md) |
| 共享 ORM / Engine / Snowflake ID | [`packages/db`](packages/db/AGENTS.md) |
| 加 HTTP 路由 / 业务编排 / DB 迁移 | [`backend`](backend/AGENTS.md) |
| 改管理后台界面 | [`frontend/admin`](frontend/admin/AGENTS.md) |
| 改桌面客户端 | [`desktop`](desktop/AGENTS.md) |

## 文档索引

按依赖层级从底到顶排列。每个模块的详细设计、接口、表关系在各自的 AGENTS.md 中。

### 基础设施层

| 模块 | 文档 | 一句话描述 |
|------|------|-----------|
| **infra** | [`packages/infra/AGENTS.md`](packages/infra/AGENTS.md) | Redis 连接管理、缓存抽象、消息队列（Streams + 延迟/重试/死信） |
| **db** | [`packages/db/AGENTS.md`](packages/db/AGENTS.md) | SQLAlchemy Base、Snowflake ID、异步 Engine 生命周期 |

### 底层能力层

| 模块 | 文档 | 一句话描述 |
|------|------|-----------|
| **llm_gateway** | [`packages/llm_gateway/AGENTS.md`](packages/llm_gateway/AGENTS.md) | LLM 模型路由/调用、Model Catalog、凭据解析、Usage 提取 |
| **retrieval** | [`packages/retrieval/AGENTS.md`](packages/retrieval/AGENTS.md) | RAG 引擎：文档处理 pipeline、Embedding 抽象、向量存储、GraphRAG |

### Agent 编排层

| 模块 | 文档 | 一句话描述 |
|------|------|-----------|
| **agent_runtime** | [`packages/agent_runtime/AGENTS.md`](packages/agent_runtime/AGENTS.md) | Agent 编排内核：PydanticAI 集成、动态工具、Guardrails、Memory |
| ├ tools | [`packages/agent_runtime/src/agent_runtime/tools/AGENTS.md`](packages/agent_runtime/src/agent_runtime/tools/AGENTS.md) | 动态工具注册、JSON Schema 校验、超时隔离与重试 |
| ├ guardrails | [`packages/agent_runtime/src/agent_runtime/guardrails/AGENTS.md`](packages/agent_runtime/src/agent_runtime/guardrails/AGENTS.md) | 输入/输出/工具调用安全 Pipeline |
| ├ memory | [`packages/agent_runtime/src/agent_runtime/memory/AGENTS.md`](packages/agent_runtime/src/agent_runtime/memory/AGENTS.md) | **单会话** Token-aware 上下文管理、摘要压缩；跨会话长期记忆见平台能力层 [`packages/memory`](packages/memory/AGENTS.md) |
| ├ config | [`packages/agent_runtime/src/agent_runtime/config/AGENTS.md`](packages/agent_runtime/src/agent_runtime/config/AGENTS.md) | 运行时配置（Pydantic Settings） |
| ├ contracts | [`packages/agent_runtime/src/agent_runtime/contracts/AGENTS.md`](packages/agent_runtime/src/agent_runtime/contracts/AGENTS.md) | 对外数据契约：请求/响应模型、枚举、流式事件 |
| ├ definition | [`packages/agent_runtime/src/agent_runtime/definition/AGENTS.md`](packages/agent_runtime/src/agent_runtime/definition/AGENTS.md) | Definition-aware 运行时的读取层 |
| └ runtime | [`packages/agent_runtime/src/agent_runtime/runtime/AGENTS.md`](packages/agent_runtime/src/agent_runtime/runtime/AGENTS.md) | 核心执行引擎：run_turn / stream_turn |

### 平台能力层

| 模块 | 文档 | 一句话描述 |
|------|------|-----------|
| **cost_analysis** | [`packages/cost_analysis/AGENTS.md`](packages/cost_analysis/AGENTS.md) | LLM 用量成本聚合 + 预算/告警 |
| **evaluation** | [`packages/evaluation/AGENTS.md`](packages/evaluation/AGENTS.md) | 评估框架：数据集、指标、LLM-as-Judge |
| **memory** | [`packages/memory/AGENTS.md`](packages/memory/AGENTS.md) | 跨会话长期记忆（pgvector）≠ agent_runtime/memory |
| **observability** | [`packages/observability/AGENTS.md`](packages/observability/AGENTS.md) | 分布式链路追踪（EventBus → Span/Trace） |

### 应用层

| 模块 | 文档 | 一句话描述 |
|------|------|-----------|
| **backend** | [`backend/AGENTS.md`](backend/AGENTS.md) | FastAPI 主应用：业务模块、路由、DI、数据库迁移 |
| **frontend** | [`frontend/admin/AGENTS.md`](frontend/admin/AGENTS.md) | React 管理后台：模型管理、Agent 管理、知识库、AI 对话 |
| **desktop** | [`desktop/AGENTS.md`](desktop/AGENTS.md) | PySide6 桌面客户端：桌宠、对话面板、截图识别、本地记忆 |

### 运维参考

| 文档 | 内容 |
|------|------|
| [docs/operations/docker-debug.md](docs/operations/docker-debug.md) | Docker 本地调试启动命令、访问地址、依赖约束、已修复 bug |
| [.env.example](.env.example) | 全部环境变量模板 |
