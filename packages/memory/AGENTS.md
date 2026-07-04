# memory — 长期记忆

> ⚠️ **消歧**：本包是**跨会话长期记忆**（PostgreSQL + pgvector 向量检索、LLM 提取/整合/注入）。与 [`agent_runtime/memory`](../agent_runtime/src/agent_runtime/memory/AGENTS.md)（**单会话** Token-aware 上下文裁剪）是**两个不同的东西**。二者通过 `MemoryInjector` 协作：本包把长期记忆注入到 agent_runtime 管理的消息列表里。

> **定位**：为 Agent 提供跨会话的持久化记忆。支持三种类型——情节(episodic, 对话摘要)、语义(semantic, 事实知识)、程序性(procedural, 用户偏好)。含存储、LLM 提取、语义检索、注入、整合(consolidation) 全套能力。

## 系统中的角色

```
backend (main.py lifespan 初始化 + modules/memory HTTP 层)
   │
   │  (可选) agent_runtime.engine —— memory_module 参数注入
   │            │ run_turn 前：检索 → 注入历史
   │            │ run_turn 后：提取 episodic/semantic → 存库 + 向量化
   ▼
        memory  ← 本包
  (Store · Extractor · Retriever · Injector · Consolidator)
   │                        │ (硬依赖, extractor/consolidator 直接 import)
   ▼                        ▼
agentlabkit-db (memory_records / memory_embeddings, pgvector)   llm_gateway (GatewayService)
```

- 被 `backend/src/main.py` 通过 `create_memory_module(session_factory=..., gateway_service=..., embedding_provider=..., settings=...)` 初始化（默认 `enabled=False`），挂到 `app.state.memory_module`。
- HTTP 层在 `backend/src/modules/memory/`。
- **agent_runtime 集成**：`packages/agent_runtime/src/agent_runtime/runtime/engine.py` 接受 `memory_module` 参数，在 run_turn 前后做检索注入与提取保存（接口就绪；backend 当前未传入）。

## 目录结构

```
packages/memory/src/memory/
├── __init__.py          # 公开 API 导出
├── config.py            # MemorySettings (LONG_TERM_MEMORY_ 前缀)
├── contracts.py         # MemoryType 枚举 / MemoryRecord / MemoryQuery
├── store.py             # MemoryStore Protocol + PostgresMemoryStore (pgvector 检索)
├── extractor.py         # MemoryExtractor Protocol + GatewayMemoryExtractor (LLM 提取)
├── retrieval.py         # MemoryRetriever (语义搜索)
├── injector.py          # MemoryInjector (记忆注入到对话历史)
├── consolidator.py      # MemoryConsolidator (旧记忆合并为摘要)
└── module.py            # MemoryModule + create_memory_module() 工厂
```

## 核心接口

### MemoryType (`contracts.py`)

```python
class MemoryType(str, Enum):   # EPISODIC="episodic" / SEMANTIC="semantic" / PROCEDURAL="procedural"
```

### MemoryStore / PostgresMemoryStore (`store.py`)

```python
@runtime_checkable
class MemoryStore(Protocol):
    async def save(self, record: MemoryRecord) -> MemoryRecord: ...
    async def save_batch(self, records: list[MemoryRecord]) -> list[MemoryRecord]: ...
    async def get(self, memory_id: int) -> MemoryRecord | None: ...
    async def search(self, query: MemoryQuery, embedding: list[float]) -> list[MemoryRecord]: ...   # pgvector 余弦相似度, 自动更新访问计数
    async def deactivate(self, memory_id: int) -> None: ...                                          # 软删除
    async def list_by_user(self, user_id, memory_type=None, page=1, page_size=20) -> tuple[list[MemoryRecord], int]: ...
    async def count_by_type(self, user_id: str) -> dict[str, int]: ...

class PostgresMemoryStore(MemoryStore):
    async def save_embedding(self, ...) -> None    # 写 memory_embeddings 表 (INSERT ... ON CONFLICT DO UPDATE)
```

### MemoryExtractor / GatewayMemoryExtractor (`extractor.py`)

```python
@runtime_checkable
class MemoryExtractor(Protocol):
    async def extract_episodic(self, messages) -> list[str]: ...
    async def extract_semantic(self, messages) -> list[str]: ...
    async def extract_procedural(self, messages) -> list[str]: ...

class GatewayMemoryExtractor:   # __init__(gateway_service, model_binding_key=""), 内部 import llm_gateway
```

### 其余组件

```python
class MemoryRetriever:     # __init__(store, embedding_provider, settings=None); retrieve(query, user_id, ...) -> 生成 embedding → 向量搜索
class MemoryInjector:      # inject(memories, history) -> 将记忆作为 SYSTEM 消息插入历史开头 (带 _priority/_memory_kind metadata)
class MemoryConsolidator:  # __init__(store, extractor); consolidate(user_id, memory_type=EPISODIC, batch_size=10) -> 合并旧记忆为摘要并 deactivate
```

### 关键数据类 (`contracts.py`)

```python
class MemoryRecord:   # id, user_id, session_id, memory_type, content, summary, source_turn_ids_json, relevance_score, access_count, last_accessed_at_utc, consolidated_from_json, is_active, expires_at_utc, ...
class MemoryQuery:    # user_id, query, memory_types, top_k=5, min_relevance=0.5
```

### 工厂 (`module.py`)

```python
def create_memory_module(*, session_factory, gateway_service=None, embedding_provider=None, settings: MemorySettings | None = None) -> MemoryModule
```

注入：`session_factory`→Store；`gateway_service`→GatewayMemoryExtractor（无则用 `_DummyExtractor`）；`embedding_provider`→Retriever；返回含 settings/store/extractor/retriever/injector/consolidator 的 MemoryModule。

## 配置

| Settings 类 | env 前缀 | 关键字段 | 默认值 |
|------|------|------|------|
| `MemorySettings` | `LONG_TERM_MEMORY_` | `enabled`、`extraction_model`、`embedding_model`、`max_memories_per_user`、`consolidation_threshold`、`retrieval_top_k`、`relevance_threshold` | `False`、`""`、`""`、`1000`、`50`、`5`、`0.5` |

## 依赖

### 内部

- `agentlabkit-db`（硬依赖）
- `llm_gateway` — **硬依赖**：`extractor.py` / `consolidator.py` 直接 `import TextGenerateRequest`
- `agent_runtime` — **可选**：`injector.py` import `AgentMessage/AgentRole` 有 ImportError fallback

### 外部

- `pydantic`、`pydantic-settings`、`sqlalchemy[asyncio]`

## 另见

- [根 AGENTS.md](../../AGENTS.md) — 全局架构与文档索引
- [agent_runtime/memory](../agent_runtime/src/agent_runtime/memory/AGENTS.md) — ⚠️ 单会话上下文管理（非本包）
- [packages/llm_gateway/AGENTS.md](../llm_gateway/AGENTS.md) — GatewayMemoryExtractor 依赖的 GatewayService
- [backend/AGENTS.md](../../backend/AGENTS.md) — memory_records/memory_embeddings 表与 HTTP 路由
