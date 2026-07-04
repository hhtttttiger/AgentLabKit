<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-03 -->

# agent_runtime/definition

## Purpose
实现 definition-aware runtime 的 Python 侧读取层：从共享数据库加载 `.NET` 管理面发布的 `AgentDefinition`（含版本、prompt、tool bindings、model binding），并通过缓存层避免频繁查询，使 `AgentRuntime` 能够按 `agent_key` 执行不同配置的 agent。

## 实施状态（来自 Agent Module Phase 4/5）

| 内容 | 状态 |
|------|------|
| `AgentDefinitionSnapshot` / `ToolBindingSnapshot` 数据模型 | ✅ 完成 |
| `AgentDefinitionLoader`（SQLAlchemy read-only ORM + async） | ✅ 完成 |
| `InMemoryAgentDefinitionCache` | ✅ 完成 |
| `AgentRuntime` 集成（engine.py 中按 definition 覆盖 prompt/model） | ✅ 完成 |

## Key Files

| File | Description |
|------|-------------|
| `models.py` | `AgentDefinitionSnapshot`：运行时所需字段的不可变快照（agent_key / system_prompt / model_binding_key / tool_bindings / guardrails_policy / handoff_policy / status）；`ToolBindingSnapshot`：单工具绑定快照 |
| `loader.py` | `AgentDefinitionLoader`：async SQLAlchemy read-only 查询；`load_by_key(agent_key)` 加载已发布 definition；内置 ORM models（`AgentDefinitionOrm` / `AgentDefinitionVersionOrm` / `AgentToolBindingOrm`）映射 `.NET` 管理的表 |
| `cache.py` | `AgentDefinitionCache` protocol + `InMemoryAgentDefinitionCache`（TTL 缓存；默认 60s）；避免每个 turn 都查库 |

## Public API

```python
# 快照数据类
AgentDefinitionSnapshot(
    agent_key, display_name, status,
    system_prompt,          # 覆盖 AgentSettings.default_system_prompt
    model_binding_key,      # 覆盖 AgentSettings.default_model（经 llm_gateway 解析）
    tool_bindings,          # list[ToolBindingSnapshot]
    guardrails_policy,      # dict，传递给 GuardrailsSettings
    handoff_policy,         # dict，传递给 HandoffPolicy
    runtime_options,        # dict，未来扩展
)
ToolBindingSnapshot(tool_name, invocation_mode, description, is_enabled)

# Loader（需 AsyncSession factory）
AgentDefinitionLoader(session_factory: async_sessionmaker)
    .load_by_key(agent_key: str) -> AgentDefinitionSnapshot | None

# Cache
AgentDefinitionCache         # protocol: get / set / invalidate
InMemoryAgentDefinitionCache(ttl_seconds=60)
    .get(agent_key) -> AgentDefinitionSnapshot | None
    .set(agent_key, snapshot)
    .invalidate(agent_key)
```

## For AI Agents

### Working In This Directory
- 本层是 **只读消费**，与 `llm_gateway.ModelCatalogRepository` 相同模式；**不向数据库写入任何数据**。
- 表名（`agent_definitions` / `agent_definition_versions` / `agent_tool_bindings`）与列名（PascalCase，使用 `mapped_column("ColumnName", ...)` 映射）由 `.NET` EF Core 管理，Python 侧只读；改动列映射前先核对 `.NET` 侧的 entity 定义。
- `load_by_key()` 只加载 `Status = "published"` 且有 `published_version_id` 的 definition；draft / archived 状态不对运行时可见。
- `AgentDefinitionSnapshot` 是不可变快照，字段变更时需同时更新 `models.py` 和 `loader.py` 中的 ORM 查询字段映射。
- 缓存 TTL 默认 60s；变更 TTL 通过构造参数传入，不要修改默认值（影响测试稳定性）。
- `AgentRuntime` 中 definition 不存在时降级为 `AgentSettings` 默认值，**不报错**；仅当 `definition_loader` 被注入时才启用 definition-aware 逻辑。

### Testing Requirements
- 变更后运行：`python3 -m pytest templates/python/agent_runtime/tests/test_definition.py`
- 全套回归：`python3 -m pytest templates/python/agent_runtime/tests/`

### Common Patterns
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from agent_runtime.definition import AgentDefinitionLoader, InMemoryAgentDefinitionCache

engine = create_async_engine(DATABASE_URL)
session_factory = async_sessionmaker(engine, expire_on_commit=False)
loader = AgentDefinitionLoader(session_factory)
cache = InMemoryAgentDefinitionCache(ttl_seconds=60)

# 在 create_agent_module(definition_loader=loader) 时注入
```

## Dependencies

### Internal
- `agent_runtime.contracts.models` — `AgentMessage`

### External
- `sqlalchemy[asyncio]>=2.0`
- `asyncpg`（PostgreSQL 异步驱动）

## See Also
- [../AGENTS.md](../AGENTS.md)
- [计划文档](../../../../../../../templates/plans/agent_plan/archive/2026-04-02-agent-module-implementation-plan.md)
