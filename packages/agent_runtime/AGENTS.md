<!-- Parent: ../AGENTS.md -->

# agent_runtime

## Purpose

`agent_runtime` 是 `agent_service` 的 Agent 编排内核，由 `agent_service` 进程内注入复用，**不作为独立部署服务**。基于自建 Agent Loop + LLM Gateway，提供生产级 agent 执行所需的核心能力：Agent Module 装配、记忆与上下文管理、Guardrails 安全 pipeline、动态工具体系、MCP 外部工具集成、Skills 能力复用、Sub-Agent 编排、事件总线、Definition-aware 运行时。

Agent 能力基于 [pi.dev](https://pi.dev/) 框架构建。

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `src/agent_runtime/contracts/` | 请求/响应数据契约（`AgentTurnRequest` / `AgentTurnResult` / `AgentTurnStreamEvent` 及消息/工具/Skill 等子模型）；传输层与编排层的稳定边界（见 `contracts/AGENTS.md`） |
| `src/agent_runtime/config/` | 运行时配置（`AgentSettings` / `MemorySettings` / `GuardrailsSettings`）；环境变量 `AGENT_RUNTIME_` 前缀（见 `config/AGENTS.md`） |
| `src/agent_runtime/runtime/` | 核心执行引擎：`AgentRuntime.run_turn()` / `stream_turn()`，拆分为 turn_prep → turn_guards → agent_loop → turn_post 等 ~14 个协作模块（见 `runtime/AGENTS.md`） |
| `src/agent_runtime/memory/` | Token-aware 上下文裁剪、摘要压缩、消息优先级、SessionStore（见 `memory/AGENTS.md`） |
| `src/agent_runtime/guardrails/` | 可组合 input / output / tool guards pipeline；内置 5 个 guard 实现 + 全局 guardrail 规则匹配（见 `guardrails/AGENTS.md`） |
| `src/agent_runtime/tools/` | 动态工具注册/过滤/执行隔离/外部 HTTP 工具框架；内置 3 个工具；向后兼容 `ToolRegistry` 封装（见 `tools/AGENTS.md`） |
| `src/agent_runtime/mcp/` | MCP client/transport/adapter/registry bridge（基于标准 `mcp` SDK）；全局配置 + definition-aware `mcp_bindings` 驱动的外部工具接入 |
| `src/agent_runtime/skills/` | Skill 契约/注册/合成 + 内置 skills；可复用能力单元 |
| `src/agent_runtime/definition/` | Agent Definition 只读加载（SQLAlchemy async）+ InMemory TTL 缓存（见 `definition/AGENTS.md`） |
| `src/agent_runtime/orchestration/` | Sub-Agent 编排：handoff（路由+切换）、delegation（子 Agent 调用）、context passing（直接/摘要传递）、深度/循环防护 |
| `src/agent_runtime/channels/` | 通道特定逻辑：voice channel 的 guardrail 评估、安全回复生成、语音段分割 |
| `src/agent_runtime/` | 顶层模块：`module.py`（装配入口）、`prompts.py`（system prompt 构建）、`errors.py`（错误枚举）、`state.py`（Agent 状态容器）、`event_bus.py`（发布/订阅事件总线）、`events.py`（类型化生命周期事件）、`__init__.py`（统一公开 API） |
| `tests/` | 模块级单元测试与集成测试（全部 pytest） |

## Key Files

| File | Description |
|------|-------------|
| `src/agent_runtime/__init__.py` | 统一公开 API 入口；所有对外使用的类/函数都从此处 import |
| `src/agent_runtime/module.py` | `AgentModule`（顶层装配体）+ `create_agent_module()` + `load_agent_module()` |
| `src/agent_runtime/runtime/engine.py` | `AgentRuntime`：核心编排引擎，`run_turn()` / `stream_turn()` / 事件订阅 / 生命周期管理（~1958 行） |
| `src/agent_runtime/runtime/loop.py` | 自建 Agent Loop：双层循环、消息队列、事件发射（~779 行） |
| `src/agent_runtime/runtime/llm_adapter.py` | LLM 调用适配：直接调用 gateway，不经过 pydantic-ai |
| `src/agent_runtime/runtime/turn_prep.py` | Turn 准备：definition 解析、settings 覆盖、skill prompt 合成 |
| `src/agent_runtime/runtime/turn_guards.py` | Turn 守卫：input guard 评估、global guardrail 拦截 |
| `src/agent_runtime/runtime/turn_post.py` | Turn 后处理：handoff 判定、output guard、结果组装 |
| `src/agent_runtime/runtime/tool_execution.py` | 工具调用分发与委托执行 |
| `src/agent_runtime/runtime/session.py` | Session 快照加载/持久化 |
| `src/agent_runtime/runtime/message_builder.py` | 消息构造与标准化 |
| `src/agent_runtime/runtime/cancel.py` | 协作式取消令牌（CancelScope / CancelToken） |
| `src/agent_runtime/contracts/models.py` | 所有 I/O 数据契约 |
| `src/agent_runtime/state.py` | `AgentState`：copy-on-write agent 状态容器 |
| `src/agent_runtime/events.py` | 类型化生命周期事件（Agent/Turn/Message/Tool 事件联合体） |
| `src/agent_runtime/event_bus.py` | `EventBus`：发布/订阅事件总线 |
| `src/agent_runtime/orchestration/router.py` | `AgentRouter`：关键词/正则路由匹配 |
| `src/agent_runtime/orchestration/handoff_manager.py` | `HandoffManager`：handoff 判定 + 目标解析 + 上下文传递 |
| `src/agent_runtime/orchestration/sub_agent_executor.py` | `SubAgentExecutor`：子 Agent turn 执行 + 深度/循环防护 |
| `src/agent_runtime/orchestration/delegate_tool.py` | `DelegateToAgentTool`：内置 delegation 工具处理器 |
| `src/agent_runtime/tools/external.py` | `HttpToolHandler` + `ExternalToolConfig`：HTTP 外部工具框架 |
| `src/agent_runtime/tools/catalog_syncer.py` | `ToolCatalogSyncer`：DB 驱动外部工具定义加载 |
| `src/agent_runtime/mcp/client.py` | `McpClientManager`：MCP server 生命周期管理与工具发现 |
| `src/agent_runtime/mcp/transport.py` | 标准 `mcp` SDK 传输适配器（stdio/sse/streamable-http） |
| `src/agent_runtime/skills/composer.py` | `SkillComposer`：skill prompt / tool binding 合并逻辑 |
| `src/agent_runtime/channels/voice.py` | `VoiceGuardrailEvaluator`：语音 guardrail 评估 + 安全回复生成 |
| `src/agent_runtime/guardrails/global_guard.py` | `GlobalGuardrailService`：全局 guardrail 规则匹配与干预 |
| `pyproject.toml` | 包定义与依赖声明（含 optional: memory / tools） |
| `conftest.py` | 共享 fixture 与路径配置 |
| `INTEGRATION_GUIDE.md` | 与 agent_service 的装配与接入规则 |

## For AI Agents

### Working In This Repository

- `agent_runtime` 是**进程内复用模块**，不是独立服务；不要为它添加 FastAPI / gRPC 入口。
- 所有对外公开的 API 必须从 `src/agent_runtime/__init__.py` 导出；子模块的内部类不应被外部直接引用。
- **模块装配入口**固定为 `create_agent_module()` / `load_agent_module()`；各子模块通过依赖注入组合。
- definition-aware runtime：`AgentTurnRequest.agent_key` → `AgentDefinitionLoader` → 覆盖 prompt/model/tools/skills；不传 `agent_key` 时降级为 `AgentSettings` 默认值。
- `run_turn()` 和 `stream_turn()` 基于自建 Agent Loop + `LlmAdapter`（`loop.py` + `llm_adapter.py`），不依赖 pydantic-ai。
- MCP 基于标准 `mcp` SDK（stdio/sse/streamable-http）；全局 MCP 通过 `AgentSettings.enable_mcp` + `mcp_servers` 启用；definition-aware agent 会在 turn 前按 `mcp_bindings` 复用/补建连接。调用方负责在应用生命周期中调用 `runtime.start()` / `runtime.stop()`。
- Skills：`SkillRegistry` 注册 + `SkillComposer` 将启用 skill 的 prompt fragment 注入 system prompt，同时合成 tool bindings。
- Sub-Agent 编排：`HandoffManager` 处理 agent 到 agent/human 的 handoff；`DelegateToAgentTool` 提供 LLM 驱动的子 agent 委托调用；`SubAgentExecutor` 管理深度上限和循环检测。
- 事件系统：`EventBus` 支持任意数量的 `EventListener` 订阅；所有状态变更通过 `AgentEvent` 子类（Agent/Turn/Message/Tool 生命周期）发射。

### Testing Requirements

```bash
# 模块级单元测试 + 集成测试（全套）
python3 -m pytest packages/agent_runtime/tests

# 仅跑某模块
python3 -m pytest packages/agent_runtime/tests/test_memory.py
python3 -m pytest packages/agent_runtime/tests/test_guardrails.py
python3 -m pytest packages/agent_runtime/tests/test_dynamic_tools.py
python3 -m pytest packages/agent_runtime/tests/test_external_tools.py
python3 -m pytest packages/agent_runtime/tests/test_definition.py
python3 -m pytest packages/agent_runtime/tests/test_runtime.py
python3 -m pytest packages/agent_runtime/tests/test_module.py
python3 -m pytest packages/agent_runtime/tests/test_mcp.py
python3 -m pytest packages/agent_runtime/tests/test_mcp_phase2.py
python3 -m pytest packages/agent_runtime/tests/test_skills.py
python3 -m pytest packages/agent_runtime/tests/test_skills_phase2.py
python3 -m pytest packages/agent_runtime/tests/test_orchestration.py
python3 -m pytest packages/agent_runtime/tests/test_tool_catalog_sync.py
```

### Common Patterns

**装配（推荐通过 agent_service 的 `load_agent_service_module()` 触发）**

```python
from agent_runtime import create_agent_module, AgentSettings

module = create_agent_module(
    settings=AgentSettings(),
    gateway=gateway_module,          # llm_gateway.GatewayModule | GatewayService
    tool_registry=my_registry,       # 可选，默认 ToolRegistry()
    definition_loader=loader,        # 可选，启用 definition-aware runtime
    context_manager=ctx_mgr,         # 可选，启用 memory
    session_store=session_store,     # 可选，启用 session 持久化
    skill_registry=skill_registry,   # 可选，启用 skills
    mcp_client_manager=mcp_mgr,      # 可选，启用 MCP
    handoff_manager=handoff_mgr,     # 可选，启用 handoff
    catalog_syncer=syncer,           # 可选，启用 DB 工具目录同步
)
```

**执行 turn**

```python
from agent_runtime import AgentTurnRequest

result = await module.runtime.run_turn(AgentTurnRequest(
    session_id="s1",
    user_message="帮我查一下最近的订单状态",
    history=[],
    agent_key="customer_support_v2",   # 可选：按 definition 路由
))
```

**订阅事件**

```python
def on_event(event):
    print(f"[{event.type}] event received")

unsub = module.runtime.subscribe(on_event)
# ... later
unsub()
```

**环境变量配置（常用）**

```bash
AGENT_RUNTIME_DEFAULT_MODEL=gpt-4.1-mini
AGENT_RUNTIME_MEMORY__ENABLED=true
AGENT_RUNTIME_MEMORY__MAX_TOTAL_TOKENS=8000
AGENT_RUNTIME_GUARDRAILS__ENABLED=true
AGENT_RUNTIME_GUARDRAILS__ENABLE_PII_MASKING=true
AGENT_RUNTIME_MCP__ENABLED=true
```

## Dependencies

### Internal

- `llm_gateway` — 模型访问、摘要调用、GatewayService

### External

- `pydantic>=2.10.0` / `pydantic-settings>=2.7.0`
- `mcp>=1.0.0` — 标准 MCP SDK（stdio/sse/streamable-http 传输）
- `agentlabkit-db>=0.1.0` — 共享数据库模型（definition / tool catalog）
- `tiktoken>=0.8.0`（optional，memory token 计数）
- `jsonschema>=4.20.0`（optional，工具参数 schema 校验）

## See Also

- [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)
- [../agent_service/AGENTS.md](../agent_service/AGENTS.md)
- [../AGENTS.md](../AGENTS.md)
