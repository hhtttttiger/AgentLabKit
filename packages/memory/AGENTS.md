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
  (Provider Registry → Store · Extractor · Retriever · Injector · Consolidator)
   │                        │ (硬依赖, extractor/consolidator 直接 import)
   ▼                        ▼
agentlabkit-db (memory_records / memory_embeddings, pgvector)   llm_gateway (GatewayProtocol)
                                   │
                                   ▼
                        Mem0 (可选, 自动提取/去重/合并)
```

- 被 `backend/src/main.py` 通过 `build_memory_module()` 初始化，挂到 `app.state.memory_module`。
- **Provider 抽象**：支持通过 `LONG_TERM_MEMORY_PROVIDER` 环境变量切换后端（默认 `mem0`，可选 `native`）。
- HTTP 层在 `backend/src/modules/memory/`。
- **agent_runtime 集成**：`packages/agent_runtime/src/agent_runtime/runtime/engine.py` 接受 `memory_module` 参数，在 run_turn 前后做检索注入与提取保存。

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
├── module.py            # MemoryModule + create_memory_module() 工厂
└── providers/           # Provider 抽象层
    ├── __init__.py      # 导出 MemoryProvider, MemoryProviderRegistry
    ├── base.py          # MemoryProvider Protocol
    ├── registry.py      # MemoryProviderRegistry (注册/发现/切换)
    ├── native_provider.py  # NativeMemoryProvider (Postgres + LLM Gateway)
    └── mem0_provider.py    # Mem0MemoryProvider (Mem0 开源库适配)
```

## 核心接口

### MemoryType (`contracts.py`)

```python
class MemoryType(str, Enum):   # EPISODIC="episodic" / SEMANTIC="semantic" / PROCEDURAL="procedural"
```

### MemoryProvider Protocol (`providers/base.py`)

```python
@runtime_checkable
class MemoryProvider(Protocol):
    name: str
    def get_store(self) -> MemoryStore: ...
    def get_extractor(self) -> MemoryExtractor: ...
    def get_embedding_provider(self) -> Any | None: ...
    async def initialize(self) -> None: ...
    async def health_check(self) -> bool: ...
```

### MemoryProviderRegistry (`providers/registry.py`)

```python
class MemoryProviderRegistry:
    def register(self, provider: MemoryProvider, *, default: bool = False) -> None: ...
    def get(self, name: str | None = None) -> MemoryProvider: ...  # 不传返回默认
    def list_providers(self) -> list[str]: ...
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
def create_memory_module(
    *,
    session_factory=None,
    gateway_service=None,
    embedding_provider=None,
    settings: MemorySettings | None = None,
    provider_registry: MemoryProviderRegistry | None = None,
    provider_name: str | None = None,
) -> MemoryModule
```

**Provider 模式**（默认）：传入 `provider_registry`，通过 `provider_name` 或 `settings.provider` 选择后端。
**Legacy 模式**：不传 `provider_registry`，直接用 `session_factory` + `gateway_service` 构建组件（向后兼容）。

## 配置

| Settings 类 | env 前缀 | 关键字段 | 默认值 |
|------|------|------|------|
| `MemorySettings` | `LONG_TERM_MEMORY_` | `enabled`、`provider`、`extraction_model`、`embedding_model`、`max_memories_per_user`、`consolidation_threshold`、`retrieval_top_k`、`relevance_threshold`、`mem0_config_path` | `True`、`"mem0"`、`""`、`""`、`1000`、`50`、`5`、`0.5`、`""` |

### Provider 切换

```bash
# 使用 Mem0（默认，自动提取/去重/合并）
LONG_TERM_MEMORY_PROVIDER=mem0

# 使用原生 Postgres + LLM Gateway
LONG_TERM_MEMORY_PROVIDER=native

# Mem0 配置文件（可选，JSON 格式）
LONG_TERM_MEMORY_MEM0_CONFIG_PATH=/path/to/mem0_config.json
```

**Native vs Mem0：**

| 特性 | Native | Mem0 |
|------|--------|------|
| 记忆提取 | LLM Gateway 手动提取 | Mem0 自动提取 |
| 去重/合并 | Consolidator 手动合并 | Mem0 内置自动去重 |
| 存储 | PostgreSQL + pgvector | PostgreSQL + pgvector（可配置） |
| 多租户 | user_id 字段隔离 | user_id 参数隔离 |
| 依赖 | 无额外依赖 | `pip install mem0ai` |

## 依赖

### 内部

- `agentlabkit-db`（硬依赖）
- `llm_gateway` — **硬依赖**（native provider）：`extractor.py` / `consolidator.py` 直接 `import TextGenerateRequest`
- `agent_runtime` — **可选**：`injector.py` import `AgentMessage/AgentRole` 有 ImportError fallback

### 外部

- `pydantic`、`pydantic-settings`、`sqlalchemy[asyncio]`
- `mem0ai` — **可选**（mem0 provider）：`pip install mem0ai`

## 另见

- [根 AGENTS.md](../../AGENTS.md) — 全局架构与文档索引
- [agent_runtime/memory](../agent_runtime/src/agent_runtime/memory/AGENTS.md) — ⚠️ 单会话上下文管理（非本包）
- [packages/llm_gateway/AGENTS.md](../llm_gateway/AGENTS.md) — GatewayMemoryExtractor 依赖的 GatewayProtocol
- [backend/AGENTS.md](../../backend/AGENTS.md) — memory_records/memory_embeddings 表与 HTTP 路由
