<!-- Parent: ../AGENTS.md -->
<!-- Updated: 2026-06-02 -->

# agent_runtime/runtime

## Purpose
`AgentRuntime` 的核心执行引擎层，将自建 Agent Loop、guardrails pipeline、memory context manager、dynamic tool registry、definition-aware 覆盖和 LLM gateway 适配组装为统一的 `run_turn()` / `stream_turn()` 执行链路。

## 重构状态（2026-06-02 架构重构）

> 参考 pi `agent-core` 包的架构模式，对 runtime 模块进行重大重构。核心目标：事件驱动架构、自建 Agent Loop、引擎拆分、移除 pydantic-ai 依赖。

### 已完成 ✅

| Phase | 内容 | 说明 |
|-------|------|------|
| Phase 1 | **事件系统** | `events.py` 类型化事件 + `event_bus.py` 订阅/发布 |
| Phase 2 | **状态管理** | `state.py` 不可变状态 + copy-on-write |
| Phase 3 | **Agent Loop (run_turn + stream_turn)** | `run_turn()` 迁移到自建 `run_agent_loop()`；`stream_turn()` 迁移到 `LlmAdapter.generate_stream()`；完全脱离 pydantic-ai 执行路径 |
| Phase 5 | **引擎拆分** | engine.py 从 2600→1513 行，拆为 ~12 个协作模块 |
| Phase 6 | **取消支持** | `cancel.py` CancelToken + CancelScope |

### 进行中 🔄

| Phase | 内容 | 说明 |
|-------|------|------|
| Phase 4 | **工具系统增强** | `StreamingToolHandler`、顺序/并行执行模式、before/after hooks（部分已在 loop.py 中实现） |

### 待完成 ⏳

| 内容 | 说明 |
|------|------|
| 移除 `mcp/client.py` 中的 `pydantic-ai.mcp` | MCP 协议客户端仍用 pydantic-ai 子模块，可替换为自建 MCP client |

## Key Files

### 核心引擎（重构后新增）

| File | Lines | Description |
|------|-------|-------------|
| `engine.py` | ~1513 | `AgentRuntime` 主编排类，瘦身后委托给子模块；`run_turn()` 和 `stream_turn()` 均使用 `LlmAdapter`（不依赖 pydantic-ai） |
| `loop.py` | ~750 | 自建 Agent Loop：双层循环、消息队列、事件发射、CancelToken 集成 |
| `llm_adapter.py` | ~400 | 直接调用 `llm_gateway`，不经过 pydantic-ai；prompt 构建 + JSON 响应解析（从 `gateway_model.py` 迁移） |
| `cancel.py` | ~60 | CancelToken + CancelScope（Python 版 AbortController/AbortSignal） |

### 引擎拆分模块（Phase 5 新增）

| File | Lines | Description |
|------|-------|-------------|
| `turn_prep.py` | ~300 | Turn 准备：definition 解析、settings 覆盖、skill 组合 |
| `turn_guards.py` | ~200 | Guardrails 执行：input/output guards、global guardrails、voice 评估 |
| `turn_post.py` | ~150 | Turn 后处理：handoff、output guards、result building |
| `tool_execution.py` | ~270 | 工具执行：dispatch、delegation、guard 集成、超时 |
| `session.py` | ~150 | Session 管理：snapshot load/save/restore |
| `message_builder.py` | ~100 | 消息构建：normalization、terminal message 替换/注释 |

### 事件与状态（Phase 1/2 新增）

| File | Lines | Description |
|------|-------|-------------|
| `../events.py` | ~80 | 类型化事件定义（Agent/Turn/Message/Tool 生命周期） |
| `../event_bus.py` | ~30 | 事件订阅/发布总线 |
| `../state.py` | ~40 | Agent 状态管理（不可变状态 + copy-on-write） |

## Public API

```python
# 主运行时
AgentRuntime(settings, gateway, tool_registry,
             definition_loader=None, context_manager=None,
             session_store=None, guards_pipeline=None,
             skill_registry=None, mcp_client_manager=None,
             handoff_manager=None, global_guardrails_repository=None)
     .run_turn(request: AgentTurnRequest, *, cancel_token=None) -> AgentTurnResult          # async — 使用自建 loop
     .stream_turn(request: AgentTurnRequest, *, cancel_token=None) -> AsyncIterator[AgentTurnStreamEvent]  # async — 使用 LlmAdapter
     .load_active_global_guardrails_snapshot() -> GlobalGuardrailsSnapshot | None

# 事件订阅
     .subscribe(listener) -> unsubscribe_callable

# 工厂函数
create_agent_runtime(...) -> AgentRuntime
```

## For AI Agents

### Working In This Directory
- `engine.py` 是编排中枢但已大幅瘦身，具体逻辑在 `turn_prep.py`、`turn_guards.py`、`turn_post.py`、`tool_execution.py` 等模块中。
- **执行链路顺序（run_turn — 自建 loop）**：
  1. 若有 `definition_loader`，加载 `AgentDefinitionSnapshot` 并覆盖 settings
  2. 运行 input guards pipeline
  3. 若有 `session_store` 且 `memory.persist_sessions=True`，load snapshot 恢复 server-managed history
  4. 若有 `context_manager`（`memory.enabled=True`），`prepare_context()` 做 token-aware 裁剪/摘要
  5. 构建 `LlmAdapter` + `LoopContext` + `LoopConfig`
  6. 调用 `run_agent_loop()`（自建双层循环，不经过 pydantic-ai）
  7. 将 `LoopResult` 转为 `AgentDecision`，进入 `_post_process_turn()`
  8. 运行 output guards pipeline + handoff + voice guardrails
  9. 若有 session_store，save snapshot
  10. 返回 `AgentTurnResult`
- **执行链路顺序（stream_turn — LlmAdapter）**：
  - 与 `run_turn` 相同的准备步骤
  - 通过 `LlmAdapter.generate_stream()` 直接调用 `gateway.generate_text_stream()`
  - `LlmAdapter` 内置 `ReplyTextStreamParser` 处理流式 JSON 解析
  - 逐 token 输出 `AgentTurnStreamEvent`
- `LoopConfig.tool_executor` 回调连接了自建 loop 和 `ToolExecution`，保持工具执行逻辑一致。
- `GatewayBackedModel` 和 `gateway_model.py` 已删除；`run_turn()` 和 `stream_turn()` 均使用 `LlmAdapter`。
- `_post_process_turn()` 现在直接接收 `raw_messages_input` 和 `loop_usage`，不再依赖 pydantic-ai 的 `AgentRunResult`。

### Testing Requirements
- 变更后运行：`PYTHONPATH=packages/agent_runtime/src python -m pytest packages/agent_runtime/tests/test_runtime.py`
- 全套回归：`PYTHONPATH=packages/agent_runtime/src python -m pytest packages/agent_runtime/tests/ --ignore=packages/agent_runtime/tests/test_real_mcp.py`
- 当前基线：**406/406 通过**

### Common Patterns
```python
from agent_runtime import create_agent_runtime, AgentTurnRequest

runtime = create_agent_runtime(settings=my_settings, gateway=my_gateway)

# 同步 turn（自建 loop）
result = await runtime.run_turn(AgentTurnRequest(
    session_id="s1", user_message="Hello", history=[]
))

# 流式 turn（LlmAdapter）
async for event in runtime.stream_turn(request):
    if event.event_type == "reply_delta":
        print(event.delta, end="")

# 事件订阅
def on_event(event):
    print(f"Event: {event.type}")
unsubscribe = runtime.subscribe(on_event)
```

## Dependencies

### Internal
- `agent_runtime.config` — `AgentSettings`
- `agent_runtime.contracts.models` — 所有请求/响应契约
- `agent_runtime.definition` — `AgentDefinitionLoader`
- `agent_runtime.guardrails` — `GuardsPipeline`
- `agent_runtime.guardrails` — `GlobalGuardrailsRepository`, `GlobalGuardrailsSnapshot`
- `agent_runtime.memory` — `ContextManager`, `SessionStore`
- `agent_runtime.tools` — `ToolRegistry`
- `agent_runtime.prompts` — `build_system_prompt()`
- `agent_runtime.events` — 类型化事件
- `agent_runtime.event_bus` — 事件总线
- `agent_runtime.state` — Agent 状态
- `llm_gateway` — `GatewayService`, `GatewayModule`

### External
- `pydantic-ai` — **仅 `mcp/client.py` 依赖**（`pydantic-ai.mcp` MCP 协议客户端）；`run_turn()`、`stream_turn()`、`tools/registry.py` 已完全不依赖

## See Also
- [../AGENTS.md](../AGENTS.md)
- [重构计划](../../docs/refactor-agent-runtime-architecture.md)
- [IMPLEMENTATION_STATUS.md](../../../IMPLEMENTATION_STATUS.md)
