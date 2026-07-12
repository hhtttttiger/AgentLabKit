# backend — FastAPI 主应用

> **定位**：AgentLabKit 的 HTTP API 层。FastAPI + 业务模块化（每个模块自包含 router + schemas + services），lifespan 管理服务初始化。

## 系统中的角色

```
frontend (React) ──HTTP──▶ backend  ← 本模块
                            │
                            ├─▶ llm_gateway / retrieval / agent_runtime (底层能力包)
                            ├─▶ cost_analysis / evaluation / memory / observability (平台能力包)
                            ├─▶ packages/db (ORM + Engine)
                            └─▶ packages/infra (Redis + Cache + Queue)
```

## 目录结构

```
backend/src/
├── main.py               # FastAPI app factory + lifespan
├── config.py             # Settings (APP_ 前缀，嵌套子模型)
├── bootstrap.py          # seed：admin 用户 + LLM 目录 + Agent 定义 + 示例
├── common/               # 跨模块共享（response / errors / crud / dependencies / auth）
└── modules/              # 业务模块（各含 router + schemas + services）
    ├── auth/             # JWT 登录认证、用户管理 CRUD、RBAC 角色控制
    ├── llm_catalog/      # LLM 模型目录管理
    ├── agent/            # Agent 定义/版本/工具/技能/MCP 管理
    ├── knowledge_base/   # 知识库/文档/分段/搜索
    ├── chat/             # 聊天会话与消息持久化
    ├── ai_invoke/        # Agent turn 执行 + 文本/嵌入生成
    ├── files/            # 文件上传存储
    ├── glossary/         # 术语管理
    ├── model_usage/      # 模型用量统计
    ├── cost_analysis/    # 成本/预算/告警 → 委托 packages/cost_analysis
    ├── evaluation/       # 评估/数据集 → 委托 packages/evaluation
    ├── memory/           # 长期记忆 → 委托 packages/memory
    └── observability/    # 链路追踪 → 委托 packages/observability
```

## 路由注册

所有路由（除 auth）均需认证，在 `main.py:_register_routers()` 注册：

| 前缀 | 来源 |
|------|------|
| `/api/auth` | `modules.auth.router` — 登录、用户管理、密码修改、个人资料 |
| `/api/llm-catalog` | `modules.llm_catalog.router` |
| `/api/agents` | `modules.agent.router` |
| `/api/agent-tools` | `modules.agent.tools_router` |
| `/api/agent-skills` | `modules.agent.skills_router` |
| `/api/agent-mcp` | `modules.agent.mcp_router` |
| `/api/knowledge-bases` | `modules.knowledge_base.router` |
| `/api/chat` | `modules.chat.router` |
| `/api/ai/invoke` | `modules.ai_invoke.router` |
| `/api/files` | `modules.files.router` |
| `/api/glossary` | `modules.glossary.router` |
| `/api/cost` | `modules.cost_analysis.router` |
| `/api/traces` | `modules.observability.router` |
| `/api/memories` | `modules.memory.router` |
| `/api/eval` | `modules.evaluation.router` |
| `/api/model-usage` | `modules.model_usage.router` |

## 配置

环境变量前缀 `APP_`，嵌套分隔符 `__`。完整列表见 [`.env.example`](../.env.example)。关键配置组：Database、JWT、File Storage、AI Gateway、Retrieval、Redis。

## 数据库

Alembic 管理迁移，迁移文件在 `backend/alembic/versions/`。

## 依赖

### 内部包

`agentlabkit-db`, `agentlabkit-infra`, `agentlabkit-retrieval`, `agent_runtime`, `agentlabkit-cost-analysis`, `agentlabkit-evaluation`, `agentlabkit-memory`, `agentlabkit-observability`

### 外部

`fastapi`, `uvicorn[standard]`, `sse-starlette`, `python-multipart`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pgvector`, `pyjwt[crypto]`, `passlib[bcrypt]`, `bcrypt`, `pydantic`, `pydantic-settings`, `loguru`, `cryptography`, `aiofiles`

## 另见

- [根 AGENTS.md](../AGENTS.md) — 全局架构与文档索引
- [packages/llm_gateway/AGENTS.md](../packages/llm_gateway/AGENTS.md) — LLM Gateway 底层能力包
- [packages/retrieval/AGENTS.md](../packages/retrieval/AGENTS.md) — RAG 引擎
