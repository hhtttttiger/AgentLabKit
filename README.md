# AgentLabKit

AI Agent 平台 — 企业级多智能体、安全护栏、知识库 RAG 全栈解决方案。
可用于快速验证DEMO。

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/fastapi-0.115+-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/pyside6-6.11+-orange.svg" alt="PySide 6">
  <img src="https://img.shields.io/badge/react-19-61dafb.svg" alt="React 19">
  <img src="https://img.shields.io/badge/postgresql-16-336791.svg" alt="PostgreSQL 16">
  <img src="https://img.shields.io/badge/license-MIT-yellow.svg" alt="License: MIT">
</p>

---

## 目录

- [架构总览](#架构总览)
- [设计亮点](#设计亮点)
- [核心能力](#核心能力)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
  - [全 Docker 模式（推荐）](#全-docker-模式推荐)
  - [本地开发模式](#本地开发模式)
- [项目结构](#项目结构)
- [模块详解](#模块详解)
- [文档索引](#文档索引)

---

## 架构总览

AgentLabKit 采用分层架构，严格遵循单向依赖：

```
┌──────────────────────────────────────────────────────────────┐
│                    传输层（框架相关，可替换）                       │
│  ┌──────────┬──────────┬──────────┬──────────┐                │
│  │ FastAPI  │ PySide6  │   ...    │   more   │  frontend     │
│  │  (当前)   │ (桌面端)  │          │          │  (React)      │
│  └────┬─────┴────┬─────┴────┬─────┴─────┬────┘                │
│       └──────────┴──────────┴───────────┘                    │
│                       │                                       │
└───────────────────────┼───────────────────────────────────────┘
                        │  全部委托给
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                    核心层（框架无关，纯 Python）                   │
│                                                              │
│  ┌──────────────────────┐  ┌────────────────────────────┐    │
│  │    Agent 编排层        │  │       平台能力层             │    │
│  │    agent_runtime      │  │  cost_analysis · evaluation │   │
│  │  (run_turn / 工具 /   │  │  memory · observability    │    │
│  │   guardrails / 短期   │  │  (成本评估/长期记忆/链路追踪) │    │
│  │   memory / 编排)      │  │                            │    │
│  └──────────┬───────────┘  └─────────────┬──────────────┘    │
│             └────────────────┬───────────┘                   │
│                              ▼                               │
│  ┌──────────────────────────────────────────────────────────┐│
│  │              底层能力层                                    ││
│  │   llm_gateway  ·  retrieval                              ││
│  │   (模型路由/调用  ·  RAG 文档处理/检索)                       ││
│  └────────────────────┬─────────────────────────────────────┘│
│                       ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  db (ORM · Snowflake ID)                                 ││
│  └────────────────────┬─────────────────────────────────────┘│
│                       ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  infra (Redis · 缓存 · 消息队列)                           ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

`backend/` 中的 FastAPI 应用仅是一层**薄壳**（`main.py` 约 150 行），核心逻辑全部位于 `packages/` 下的框架无关包中。

---

## 设计亮点

### 🔌 模块可替换

每个 `packages/<name>` 是独立的 Python 包，有明确的接口边界。任何一个模块都可以被单独替换：

| 模块 | 替换场景 |
|------|----------|
| `llm_gateway` | 切换到新的 LLM Provider，或接入内部模型平台 |
| `retrieval` | 从 pgvector 迁移到 Milvus / Qdrant / Elasticsearch |
| `agent_runtime` | 替换编排策略，或接入第三方 Agent 框架 |
| `memory` | 换成更复杂的记忆管理方案（如 MemGPT） |
| `observability` | 从 EventBus 切换到 OpenTelemetry 采集器 |

### 🐚 Web 层只是壳

FastAPI 仅负责 HTTP 参数解析和路由注册，不包含任何业务逻辑。核心层全部在 `packages/` 中以框架无关的纯 Python 实现，可以零成本切换传输层：

```
FastAPI  →  gRPC  →  ...  →  more
   ↓          ↓        ↓         ↓
         同一套 packages/*
```

### 🎯 单一入口

- **LLM 调用必须经过 `llm_gateway`** — 统一管理 API Key、限流、熔断、用量记录
- **文档/RAG 必须经过 `retrieval`** — 统一管理分块策略、Embedding、向量检索

杜绝各处散落 `openai.chat.completions.create()` 或裸调 embedding API 的混乱。

### 🧩 零框架锁定

Agent 循环直接调用 LLM Gateway，不依赖 LangChain / pydantic-ai / CrewAI 等第三方 Agent 框架。工具系统、护栏管道、多智能体编排全部自建，升级或替换不受框架约束。

### 🔗 Worker 解耦

文档索引是 CPU/IO 密集型操作，独立为 worker 进程运行，与 web 服务通过 Redis Streams 异步解耦。web 进程只负责 enqueue，索引失败不影响 API 响应。

### 🎯 编排与执行分离

工作流引擎遵循**生成与执行分离**的设计原则：
- **编排是 LLM 的能力**：根据用户意图 + Agent 能力自动生成确定性流程
- **执行是引擎的能力**：按流程定义确定性执行，无需实时 LLM 决策
- **步骤类型丰富**：工具调用、子 Agent 委托、人工确认暂停、条件分支
- **显式数据流**：通过 InputRef 显式映射步骤间数据，避免隐式状态传递

---

## 核心能力

### Agent 运行时核心
- **Agent 循环**：由 [pi](https://pi.dev/) 转写，支持阻塞/流式
- **动态工具系统**：运行时注册/注销，支持内置、MCP、HTTP 外部三种工具源
- **智能体定义**：数据库驱动的版本化配置，含工具/技能/模型绑定
- **上下文管理**：Token-aware 窗口 + LLM 摘要压缩

### 确定性工作流编排
- **LLM 生成流程**：根据用户意图 + Agent 能力（tools/MCP/skills）自动生成确定性工作流
- **DAG 执行引擎**：按步骤顺序/分支驱动执行，支持工具调用、子 Agent 委托、人工确认、条件分支
- **状态持久化**：支持 human_gate 暂停/恢复，checkpoint 持久化
- **流式事件**：实时产出执行进度事件（WorkflowStreamEvent）

### 安全护栏
- **4 层护栏管道**：输入 / 输出 / 工具参数 / 全局规则
- **语音安全**：实时语句级评估，支持安全回复、转人工/转 Agent

### 多智能体编排
- Agent-to-Agent 交接、子智能体委派（深度限制 + 循环检测）、路由匹配

### MCP 协议集成
- stdio / SSE / streamable-HTTP 三种传输，自动工具发现，按 Agent 粒度白名单

### 知识库 RAG
- 混合检索：pg_trgm + 向量嵌入 + RRF 融合，keyword / semantic / hybrid 三种模式

### 用户管理
- JWT 认证 + bcrypt 密码加密
- RBAC 角色控制（admin / member）
- 用户 CRUD（创建、编辑、停用）
- 个人资料编辑、密码修改

### 平台能力
- 长期记忆 · LLM 网关 · 可观测性 · 评估框架 · 成本分析

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | Python 3.12+, FastAPI, Uvicorn, SQLAlchemy 2.0 (async) |
| **数据库** | PostgreSQL 16 + pgvector (向量检索) |
| **缓存/队列** | Redis 7 (async, hiredis), Redis Streams |
| **桌面客户端** | PySide6 (Qt for Python), SQLite |
| **前端** | React 19, TypeScript, Vite, Zustand, React Query, Tailwind CSS 4 |
| **测试** | pytest, pytest-asyncio, Vitest |
| **基础设施** | Docker Compose (PostgreSQL + Redis + 应用服务) |

---

## 快速开始

### 前置条件

- Docker + Docker Compose v2
- macOS: 推荐 [Colima](https://github.com/abiosoft/colima) 作为 Docker runtime

### 全 Docker 模式（推荐）

```bash
# 克隆仓库
git clone https://github.com/your-org/agentlabkit.git
cd agentlabkit

# 复制环境变量配置
cp .env.example .env

# 一键启动所有服务
docker compose up --build
```

启动后访问：

| 服务 | 地址 |
|------|------|
| **管理后台** | http://localhost:3000/admin/ |
| **后端 API** | http://localhost:8000/health |
| **数据库** | localhost:5432 (app / devpassword / agentlabkit) |
| **Redis** | localhost:6379 |

默认账号：`admin / admin`

### 本地开发模式

基础设施用 Docker，后端和前端在本地运行，改代码即时生效。

```bash
# 1. 启动基础设施
docker compose up -d postgres redis
# 或：make up

# 2. 后端
cd backend
python3 -m venv .venv
source .venv/bin/activate

# 安装所有本地包（按依赖顺序）
pip install -e ../packages/db
pip install -e ../packages/infra
pip install -e ../packages/retrieval
pip install -e ../packages/cost_analysis
pip install -e ../packages/observability
pip install -e ../packages/memory
pip install -e ../packages/evaluation
pip install -e ../packages/llm_gateway
pip install -e ../packages/agent_runtime
pip install -e ".[dev]"

# 数据库迁移 + 种子数据
PYTHONPATH=src alembic upgrade head
PYTHONPATH=src python -m bootstrap

# 启动后端
PYTHONPATH=src uvicorn main:create_app --factory --host 0.0.0.0 --port 8000 --reload

# 3. 启动 Worker（另一个终端，文档索引消费者）
cd backend && source .venv/bin/activate
PYTHONPATH=src python -m worker
# 或：make worker

# 4. 前端
cd frontend/admin
npm install
npm run dev        # http://localhost:5173
```

环境变量在项目根目录 `.env` 文件中配置，默认值已适配本地开发。详见 [`.env.example`](.env.example)。

> 💡 更多本地调试细节见 [docs/operations/docker-debug.md](docs/operations/docker-debug.md) 和 [docs/operations/local-debug.md](docs/operations/local-debug.md)。

#### Claude Code 用户：一键启动

项目内置了 `/local-dev` skill（[`SKILL.md`](.claude/skills/local-dev/SKILL.md)），自动完成以上全部步骤（Docker 基础设施 → 后端 → Worker → 前端）。在 Claude Code 中输入：

```
/local-dev
```

Skill 会检测已有服务状态，已运行的服务会被跳过（秒级恢复），只在首次或 `make reset` 后执行完整初始化。

### 桌面客户端

独立的 PySide6 桌面应用，直接调用 `packages/` 层，不依赖 FastAPI 后端。

```bash
# 安装依赖
pip install PySide6
pip install -e packages/llm_gateway
pip install -e packages/memory

# 首次运行会生成配置文件
QT_QPA_PLATFORM=wayland python desktop/main.py
# macOS/Windows 不需要设置 QT_QPA_PLATFORM
```

编辑 `~/.config/agentlabkit/desktop.toml` 配置 LLM 提供商：

```toml
[llm]
provider = "openai"                          # openai | anthropic
base_url = "https://api.deepseek.com/v1"     # 兼容 OpenAI 格式的 API
api_key = "sk-xxx"
model = "deepseek-chat"
```

详见 [docs/desktop-app-plan.md](docs/desktop-app-plan.md)。

---

## 项目结构

```
agentlabkit/
├── backend/                  # FastAPI 主应用（业务模块 + HTTP API）
│   ├── src/
│   │   ├── main.py           # 应用入口
│   │   ├── bootstrap.py      # 种子数据初始化
│   │   ├── worker.py         # 文档索引 worker 入口
│   │   ├── config.py         # 应用配置
│   │   ├── common/           # 公共模块（auth, CRUD, errors, schemas）
│   │   ├── modules/          # 业务模块（知识库, LLM 目录, Agent 管理, 对话）
│   │   └── runtime/          # 运行时引导
│   ├── alembic/              # 数据库迁移
│   └── tests/                # 后端测试
│
├── desktop/                  # PySide6 桌面客户端（桌宠 + 对话面板）
├── frontend/
│   └── admin/                # React 管理后台
│
├── packages/                 # 可复用 Python 包（按依赖层级排列）
│   ├── infra/                # Redis 连接、缓存、消息队列
│   ├── db/                   # SQLAlchemy Base、Snowflake ID
│   ├── retrieval/            # RAG 引擎（文档处理、Embedding、向量检索）
│   ├── llm_gateway/          # LLM 网关（模型路由、Provider 适配、限流熔断）
│   ├── agent_runtime/        # Agent 编排内核（运行时、工具、护栏、编排）
│   │   └── workflow/         # 确定性工作流引擎（LLM 生成 + 确定性执行）
│   ├── memory/               # 跨会话长期记忆（pgvector）
│   ├── observability/        # 分布式链路追踪
│   ├── cost_analysis/        # 用量成本聚合
│   └── evaluation/           # 评估框架
│
├── docker-compose.yml        # Docker 编排配置
├── Makefile                  # 常用命令速查
├── .env.example              # 环境变量模板
├── docs/                     # 技术文档
│   ├── architecture/         # 架构设计
│   └── operations/           # 运维调试
├── AGENTS.md                 # 架构总览与文档索引（面向 AI 和协作者）
└── README.md                 # 本文件
```

---

## 模块详解

### 底层能力层

#### `llm_gateway` — LLM 模型网关

系统**唯一**调用 LLM API 的入口。核心特性：

- **多 Provider 支持**：OpenAI + OpenAI-compatible 适配器架构
- **模型目录**：数据库驱动的版本化模型配置，含路由策略、限流策略、重试策略
- **4 层容错**：SDK 异常映射 → 指数退避重试 → 令牌桶限流 → 熔断器
- **凭据解析**：加密存储 API Key，支持 instance/env 多级解析
- **用量记录**：完整的 model_request_logs 写入，含 token 计数和延迟

#### `retrieval` — RAG 知识库引擎

系统**唯一**处理文档/Embedding/向量检索的引擎：

- **文档 Pipeline**：导入 → 分块 → Embedding → 向量存储
- **混合检索**：pg_trgm 文本相似度 + 向量嵌入 + RRF 融合
- **三种检索模式**：`keyword` / `semantic` / `hybrid`
- **GraphRAG**：知识图谱存储接口

### Agent 编排层

#### `agent_runtime` — Agent 编排内核

Agent 核心改写自 [pi](https://pi.dev/)（[`earendil-works/pi`](https://github.com/earendil-works/pi)），并在此基础上扩展：

- **Agent 循环**：直接调用 LLM Gateway，支持阻塞/流式
- **动态工具系统**：运行时注册/过滤/执行，支持内置/MCP/HTTP 外部工具
- **安全护栏**：4 层安全管道（输入/输出/工具参数/全局规则）
- **语音通道**：实时语句级安全评估、安全回复生成
- **多智能体编排**：Agent 交接、子智能体委派、路由匹配
- **MCP 集成**：支持 stdio/SSE/HTTP 传输，自动工具发现
- **智能体定义**：数据库驱动的版本化 Agent 配置
- **上下文管理**：Token-aware 裁剪 + LLM 摘要
- **确定性工作流**：LLM 生成流程定义 → 引擎确定性执行（详见 [`workflow/`](packages/agent_runtime/src/agent_runtime/workflow/)）

#### 工作流引擎详解

工作流引擎位于 [`packages/agent_runtime/src/agent_runtime/workflow/`](packages/agent_runtime/src/agent_runtime/workflow/)，提供确定性多步骤流程编排能力。

**核心理念**：编排是 LLM 的能力（生成），不是用户的能力（拖拉拽）；执行是引擎的能力（确定性），不是 LLM 的能力（实时决策）。

**架构设计**：
```
用户意图 + Agent 能力
        ↓
   WorkflowGenerator (LLM)
        ↓
   WorkflowDef (流程定义)
        ↓
   WorkflowEngine (确定性执行)
        ↓
   WorkflowResult (执行结果)
```

**四种步骤类型**：

| 类型 | 说明 | 示例 |
|------|------|------|
| `tool` | 调用注册的工具 | 查询订单、发送通知 |
| `agent` | 委托给子 Agent | 数据分析、内容生成 |
| `human_gate` | 暂停等待人工确认 | 退款确认、审批流程 |
| `condition` | 条件分支 | 资格检查、状态判断 |

**数据流设计**：
- `$user_input` — 用户原始输入
- `$steps.<step_id>.<key>` — 上游步骤输出
- `$const:<value>` — 常量值

**使用示例**：
```python
from agent_runtime.workflow import WorkflowGenerator, WorkflowEngine

# 1. LLM 生成工作流
generator = WorkflowGenerator(gateway_service)
workflow = await generator.generate(
    agent_definition=agent_def,
    user_intent="用户想要退款订单 #12345",
)

# 2. 确定性执行
engine = WorkflowEngine(step_executor, state_store)
result = await engine.run_workflow(workflow, "ORDER-12345", context)

# 3. 流式执行（可选）
async for event in engine.stream_workflow(workflow, user_input, context):
    print(f"Step {event.step_id}: {event.event_type}")
```

**详细文档**：[`packages/agent_runtime/src/agent_runtime/workflow/AGENTS.md`](packages/agent_runtime/src/agent_runtime/workflow/AGENTS.md)

### 平台能力层

#### `memory` — 长期记忆
跨会话 episodic/semantic 记忆提取、注入、合并（pgvector）。

#### `observability` — 可观测性
EventBus 驱动的分布式链路追踪（Span/Trace）。

#### `evaluation` — 评估框架
数据集管理、LLM-as-Judge 质量评估、可插拔指标。

#### `cost_analysis` — 成本分析
按模型/Agent/时间段聚合 token 用量和成本。

---

## 文档索引

### 总览

| 文档 | 内容 |
|------|------|
| [`AGENTS.md`](AGENTS.md) | 架构总览、分层依赖、快速定位表 |
| [`docs/operations/docker-debug.md`](docs/operations/docker-debug.md) | Docker 启动命令、访问地址、已修复 bug |
| [`docs/operations/local-debug.md`](docs/operations/local-debug.md) | 本地开发完整指南（后端 + 前端 + Worker） |
| [`docs/desktop-app-plan.md`](docs/desktop-app-plan.md) | 桌面客户端规划与进度 |
| [`.env.example`](.env.example) | 全部环境变量模板 |

### 子模块

| 模块 | 文档 |
|------|------|
| infra | [`packages/infra/AGENTS.md`](packages/infra/AGENTS.md) |
| db | [`packages/db/AGENTS.md`](packages/db/AGENTS.md) |
| llm_gateway | [`packages/llm_gateway/AGENTS.md`](packages/llm_gateway/AGENTS.md) |
| retrieval | [`packages/retrieval/AGENTS.md`](packages/retrieval/AGENTS.md) |
| agent_runtime | [`packages/agent_runtime/AGENTS.md`](packages/agent_runtime/AGENTS.md) |
| cost_analysis | [`packages/cost_analysis/AGENTS.md`](packages/cost_analysis/AGENTS.md) |
| evaluation | [`packages/evaluation/AGENTS.md`](packages/evaluation/AGENTS.md) |
| memory | [`packages/memory/AGENTS.md`](packages/memory/AGENTS.md) |
| observability | [`packages/observability/AGENTS.md`](packages/observability/AGENTS.md) |
| backend | [`backend/AGENTS.md`](backend/AGENTS.md) |
| frontend | [`frontend/admin/AGENTS.md`](frontend/admin/AGENTS.md) |

---

## License

MIT
