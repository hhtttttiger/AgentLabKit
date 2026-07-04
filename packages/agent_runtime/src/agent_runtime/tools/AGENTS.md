<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-07 -->

# agent_runtime/tools

## Purpose
提供动态工具体系：统一元信息注册、definition-aware 过滤、JSON Schema 参数校验、超时隔离与指数退避重试执行，取代原硬编码的单工具 `ToolRegistry`。

## 实施状态

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | `ToolSpec`/`ToolBinding`/`ToolExecutor`/`ToolFilter`/`DynamicToolRegistry`、3 个内置工具、77 个单元测试 | ✅ 完成 |
| Phase 2 | ToolFilter 与 definition-aware binding 深度对齐、description 覆盖、`GET /v1/tools` API | ✅ 完成 |
| Phase 3 | `ExternalToolConfig`/`HttpToolHandler` 外部工具框架、Custom Tools 文档 | ✅ 完成 |

## Key Files

| File | Description |
|------|-------------|
| `contracts.py` | `ToolSpec`（不可变元信息）、`ToolBinding`（per-agent binding）、`ToolHandler` protocol、`ToolResult`、`ToolExecutionContext` |
| `registry.py` | `DynamicToolRegistry`（主注册表）+ `ToolRegistry`（向后兼容封装）+ `HandoffPolicy` / `KnowledgeProvider` 协议及默认实现 |
| `executor.py` | `ToolExecutor`：schema 校验 → asyncio 超时 → 指数退避重试 → 错误隔离；失败返回结构化错误，不向外抛异常 |
| `filter.py` | `ToolFilter`：按 `ToolBinding.invocation_mode`（auto_only / whitelist / disabled）过滤 registry 中已注册工具 |
| `schema_validator.py` | `SchemaValidator`：`jsonschema` 校验 + 内置 fallback（无 jsonschema 依赖时降级为必填字段检查） |
| `external.py` | `ExternalToolConfig`（HTTP 外部工具配置）+ `HttpToolHandler`（HTTP 外部工具基类；Phase 3）|
| `builtin/calculator.py` | `CalculatorTool`：安全算术表达式求值 |
| `builtin/knowledge_search.py` | `KnowledgeSearchTool`：向量知识库检索，通过 `KnowledgeProvider` 注入 |
| `builtin/time_now.py` | `TimeNowTool`：返回当前 UTC 时间 |

## Public API

```python
# 元数据
ToolSpec(name, description, parameters_schema, tags=(), timeout_seconds=30.0, max_retries=1)
ToolBinding(tool_name, invocation_mode, description=None, is_enabled=True)
ToolResult(output=None, error=None, metadata={})
ToolExecutionContext(session_id, agent_key, knowledge_provider, tool_bindings)

# ToolHandler protocol（任何实现此协议的对象都可注册）
class ToolHandler(Protocol):
    async def execute(self, ctx: ToolExecutionContext, **kwargs) -> ToolResult: ...

# 注册与查询
registry = DynamicToolRegistry()
registry.register(spec, handler)
registry.unregister(tool_name)
registry.get_spec(tool_name) -> ToolSpec | None
registry.list_specs() -> list[ToolSpec]

# 向后兼容封装（保持与旧 ToolRegistry 相同 API）
ToolRegistry(knowledge_provider=None, handoff_policy=None, dynamic_registry=None)
    .tool_definitions(settings) -> list[ToolDefinition]

# 过滤
ToolFilter(registry).filter(bindings: list[ToolBinding]) -> list[ToolSpec]

# 执行（带隔离）
ToolExecutor(registry).execute(tool_name, ctx, args) -> ToolResult

# 内置工具（注册时按 spec 协议使用）
KnowledgeSearchTool() / TimeNowTool() / CalculatorTool()
```

## For AI Agents

### Working In This Directory
- **向后兼容**：`ToolRegistry` 是 `DynamicToolRegistry` 的封装，保持旧调用方零修改；不要删除或改变 `ToolRegistry` 的公开方法签名。
- `DynamicToolRegistry` 是新代码应直接使用的主接口；内置工具通过 `register()` 动态注册，不要在 registry 里硬编码工具列表。
- `ToolExecutor` 保证执行不向外抛异常；失败通过 `ToolResult.error` 返回。若需自定义错误处理，在 handler 内部处理，不要在 executor 外层 try/catch。
- `ToolFilter.invocation_mode` 语义：`auto_only` = LLM 可自主调用；`whitelist` = 仅允许列表内工具；`disabled` = 不可用。修改过滤逻辑时保持此语义不变。
- Phase 2（ToolFilter 与 definition binding 深度对齐）依赖 `definition/loader.py` 中的 `AgentDefinitionLoader`；实施前先确认 definition 层已稳定。
- External 工具（HTTP/gRPC）作为扩展点预留，不要在现有 `ToolHandler` protocol 中引入网络调用假设。

### Testing Requirements
- 变更后运行：`python3 -m pytest templates/python/agent_runtime/tests/test_dynamic_tools.py`
- 全套回归（含向后兼容验证）：`python3 -m pytest templates/python/agent_runtime/tests/`

### Common Patterns
```python
from agent_runtime import DynamicToolRegistry, ToolSpec, ToolResult, ToolExecutionContext

registry = DynamicToolRegistry()

# 注册自定义工具
spec = ToolSpec(
    name="my_tool",
    description="Does something useful",
    parameters_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    timeout_seconds=10.0,
)

class MyToolHandler:
    async def execute(self, ctx: ToolExecutionContext, **kwargs) -> ToolResult:
        return ToolResult(output=f"result for {kwargs['query']}")

registry.register(spec, MyToolHandler())
```

## Dependencies

### Internal
- `agent_runtime.contracts.models` — `AgentMessage`, `ToolExecutionRecord`
- `agent_runtime.definition.models` — `ToolBindingSnapshot`（Phase 2）

### External
- `jsonschema`（optional；不安装时降级为内置字段检查）

## See Also
- [../AGENTS.md](../AGENTS.md)
- [计划文档](../../../../../../../templates/plans/agent_plan/archive/2026-04-02-agent-dynamic-tools-plan.md)
