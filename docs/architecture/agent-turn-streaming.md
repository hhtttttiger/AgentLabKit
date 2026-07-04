# AGENT_TURN_STREAMING.md — Agent Turn 流式执行接线（进度记录）

> 记录「AI 对话选 agent 时真正运行 agent、并把执行轨迹流回前端」这项工作的现状、实现要点与待办。
> 范围：MVP = 回复 + 知识库工具；外部 HTTP 工具 / MCP / handoff 留 Phase 2。

## 背景

此前 AI 对话里选 agent **根本没有跑 agent**：后端两个执行端点是 501 桩，`agent_runtime` 引擎（`packages/agent_runtime`，已实现且有测试）从未被 HTTP 层调用。前端 `streamAgentChatMessage` 打过去只会 501，trace 面板永远空。

本次把 `POST /api/ai/invoke/agents/{agent_key}/turn/stream` 接到了 `agent_runtime.stream_turn`，让选 agent 聊天时真正运行 agent、前端能看到执行轨迹，并落一条 `agent_execution_audits`。

## 数据流（一次 agent 对话）

```
前端 streamAgentChatMessage
  └─ POST /api/ai/invoke/agents/{key}/turn/stream   (body: Message/SessionId/History, PascalCase)
       │  ai_invoke/router.py: agent_turn_stream
       │   ├─ loader.load(agent_key) → AgentDefinitionSnapshot（解析已发布版本，未发布→404）
       │   └─ run_agent_turn_stream(...)            (modules/ai_invoke/agent_turn.py)
       │        ├─ AgentTurnRequest(agent_key, agent_version, history, trace_id)
       │        ├─ async for ev in runtime.stream_turn(req):
       │        │     map_stream_event(ev)  →  SSE data: {type, runId, sessionId, traceId, ...}
       │        ├─ except AgentError → error 事件（runtime 是抛异常、不 yield error）
       │        ├─ finally: data: [DONE] + write_audit(...)
       │        └─ StreamingResponse(media_type="text/event-stream")
```

前端 SSE 事件契约见 `frontend/admin/src/modules/ai-chat/lib/contracts.ts:117`（`AgentStreamEvent`）。
前端解析/合并逻辑（`api.ts`、`lib/agent-trace-merge.ts`）**本次未改动**，只补后端事件。

## 改动清单

| 文件 | 类型 | 说明 |
|---|---|---|
| `backend/src/modules/agent/definition_loader.py` | 新增 | `BackendAgentDefinitionLoader`：后端 ORM → `AgentDefinitionSnapshot` 适配器，实现 runtime 的 `AgentDefinitionLoader` 协议（`load` + `check_revision`）。带内存缓存。 |
| `backend/src/modules/ai_invoke/agent_turn.py` | 新增 | `map_stream_event`（runtime snake_case → 前端 camelCase，注入 `runId`）、`run_agent_turn_stream`（驱动 `stream_turn`、捕 `AgentError`→error、末尾 `[DONE]`）、`write_audit`。 |
| `backend/src/modules/ai_invoke/router.py` | 改 | 替换两个 501 桩为真实实现；修正请求体为前端一致的 PascalCase（`Message`/`SessionId`/`History`）；未发布 agent→404。 |
| `backend/src/main.py` | 改 | lifespan 里构造 `agent_runtime` 挂到 `app.state.agent_runtime` / `app.state.agent_definition_loader`；注册内置工具（见下）。 |
| `backend/src/modules/agent/builtin_tools.py` | 新增 | `register_builtin_tools()`：把 `agent_runtime` 自带的 `time_now`/`calculator` 注册进 `ToolRegistry`（`knowledge_search` 已在 `__post_init__` 自动注册，另两个原本是「死代码」）。 |
| `backend/src/modules/agent/seed.py` | 改 | 新增幂等 `seed_clock_agent()`：seed 一个 `clock` demo agent（version 1，绑 `time_now`，低 temperature + 明确提示词），专门验证工具闭环。 |
| `backend/src/bootstrap.py` | 改 | bootstrap 里调用 `seed_clock_agent`（注意：resume 时也必须跑 bootstrap 才能种出它）。 |
| `packages/llm_gateway/.../model_catalog/service.py` | 改 | `resolve_candidates` 加 binding-fallback：传入值既不是 model_key、却是已注册 binding_key 时，按 binding 解析出真正的 model_key。修掉了 agent_runtime 把 `model_binding_key` 当 model_key 传、gateway 又按 model_key 解析的接缝 bug。 |
| `backend/tests/test_agent_turn.py` | 新增 | 事件映射（8 种）+ 流式 happy/error 路径单测。 |
| `backend/tests/test_agent_definition_loader.py` | 新增 | loader 映射 / 禁用 / 未发布 / 未知 / 缓存单测（fake session，无 DB）。 |
| `backend/tests/test_builtin_tools.py` | 新增 | 注册后 `time_now`/`calculator`/`knowledge_search` 均可按 binding 解析为 tool definition。 |
| `packages/llm_gateway/tests/test_resolver_binding_fallback.py` | 新增 | binding-key 当 model_key 传 → 解析到真正 model_key；真 model_key 仍直连；未知值仍 MODEL_NOT_FOUND。 |

## 事件映射（runtime → 前端 SSE）

每条都注入 `runId` / `sessionId` / `traceId` / `agentKey` / `agentVersion`（runtime 事件里没有 `runId`，由后端按 turn 生成 uuid 注入）。

| runtime `event_type` | 前端 `type` | 关键字段 |
|---|---|---|
| `turn_context` | `context` | `appliedSkills` |
| `reply_delta` | `reply_delta` | `delta`（增量） |
| `reply_completed` | `completed` | `replyText`, `usage`, `status:"succeeded"` |
| `tool_call` | `tool_call` | `toolName`, `toolArguments`, `toolEvent` |
| `tool_result` | `tool_result` | `toolEvent` |
| `delegation_delta` | `delegation_delta` | `delta`, `delegationAgentKey` |
| `handoff` | `handoff` | `replyText`, `handoffReason`, `usage` |
| （`AgentError` 抛出） | `error` | `errorCode`, `errorMessage`, `status:"failed"` |

嵌套：`tool_event`→`toolEvent`、`usage`→`usage`、`applied_skills`→`appliedSkills` 均 snake→camel。

## 关键约束 / 已踩的坑

1. **Schema 不匹配**：`agent_runtime` 自带的 `SqlAlchemyAgentDefinitionLoader`（`packages/agent_runtime/.../definition/loader.py`）是按 `.NET` 的 PascalCase 物理列写的（`"Status"` / `"PublishedVersionId"` / `"SystemPromptTemplate"` / `"RuntimeOptionsJson"` …），与后端真实表（`backend/src/modules/agent/models.py` 的 snake_case：`published_version` / `system_prompt` / `extra_json` / `agent_version_id` …）**对不上**，所以另写了 `BackendAgentDefinitionLoader`，不能直接复用。

2. **retrieval 必须惰性耦合**：`modules/knowledge_base/knowledge_provider.py` 在模块顶层 `from .retrieval_service import ...`，而 `retrieval_service.py` 又 `from retrieval.engines.local_engine.processing import ...`（→ langchain 依赖）。早期版本在 lifespan 里**无条件 import** 了它，导致 `retrieval_enabled=false`（local-dev 默认）时也把 retrieval/langchain 链拉进来，retrieval 包未就绪就直接整个 API 起不来。
   **修复**：`BackendKnowledgeProvider` 改为惰性 import（仅 `retrieval_service` 真正存在时才引）+ 套 `try/except`，retrieval 半残时降级为禁用知识库工具，不阻断启动。**结论：lifespan 里永远不要无条件 import retrieval 链。**

3. **`default` agent 没有工具**：`seed.py` 建的 `default` 是纯助手（`tool_bindings=0`、`kb_bindings=0`，DB 实查确认）。所以它跑起来就是直接回复一段文字，肉眼上和裸模型一样 —— 区别只在 trace 面板有 `context→reply→completed` 三步 + 一行审计，**不会有 `tool_call`**。要看到工具调用必须有带工具/知识库绑定的 agent。

4. **gateway 「Model not found」的真正原因（已修复）**：**不是**目录缓存不刷新，而是 `agent_runtime` 与 `llm_gateway` 的一个接缝 bug —— `turn_prep._normalize_request`（`runtime/turn_prep.py:164`）把 agent 的 `model_binding_key`（如 `mimo-v2-flash-chat`）直接塞进 `request.model`，但 gateway 的 `resolve_candidates`（`core/service.py:113`）按 **model_key** 解析（且 binding_key 走硬编码默认 `gateway.default_text`）。`mimo-v2-flash-chat` 是 binding 不是 model（真 model_key 是 `mimo-v2-flash`）→ MODEL_NOT_FOUND。**这会让 default agent 也一起挂**。
   **修复**：`resolve_candidates` 顶部加 binding-fallback —— 传入值不是真 model_key 却是已注册 binding_key 时，改按 binding 解析出 model_key。纯加性，只影响「传了 binding_key」的场景。**重启后端**（uvicorn `--reload` 只 watch `backend/`，不 watch `packages/`，改了 gateway 必须重启进程）后 default + clock agent 均恢复。

## 当前验证状态

- ✅ 20 个单测全绿：`test_agent_turn`(8) + `test_agent_definition_loader`(6) + `test_builtin_tools`(3) + `test_resolver_binding_fallback`(3)。
- ✅ live 后端实测：`POST /agents/default/turn/stream` 正确产出 `context` 事件（带 `runId`/`agentKey`/`agentVersion`）。
- ✅ `agent_execution_audits` 表落了对应 run_id 的审计行（status/error_message/duration 齐全）。
- ✅ default + clock agent 均能正常回复（gateway 接缝 bug 已修，见下）。
- ✅ **工具闭环已打通**（`clock` agent 问时间）：trace 出现完整 `context → tool_call(time_now, args={timezone_offset_hours:8}) → tool_result(UTC+8 时间) → reply_delta* → completed`；审计行 `tool_calls_json` 含 `time_now` 的 started+success 两条记录。mimo-v2-flash **支持** function-calling 且能正确推断时区参数。

运行/测试所需环境变量（local-dev 约定）：
```
PYTHONPATH=src:../packages/llm_gateway/src:../packages/agent_runtime/src
```

> 注：`packages/llm_gateway/tests/test_catalog_integration.py` 与 `test_model_catalog_repository.py` 目前因 `from ...orm_models import LlmModelCardFeatureOrm` 报 ImportError（该类已从 `orm_models` 移除，测试未跟上）—— 属既有 stale，与本次无关。改了 gateway 后回归跑 `test_resolver_binding_fallback.py` + `test_gateway_core.py` + `test_module.py` 即可（12 绿）。

## MVP 范围 vs Phase 2

**MVP（本次完成）**：定义加载 + `stream_turn` 接线 + 事件映射 + SSE + 审计；知识库工具在 retrieval 健康时可用。

**Phase 2（未做，定义里已保留 schema 下发）**：
- 绑定的**外部 HTTP 工具**（`agent_tools` 表 `source=external`）注册成可执行 handler。
- **MCP 工具**执行（接 `mcp_client_manager` + 已加载的 `mcp_bindings`）。
- `handoff_policy` / `response_policy` / `guardrails_policy` 从 `extra_json` 细化解析；agent 间 handoff/delegation。
- skill 绑定接入 `SkillComposer`。
- `definition_loader` 的 `refresh_if_stale()` 定时刷新缓存。

## 下一步（待用户定）

- ~~**A. 快速验证工具闭环（不依赖 retrieval）**~~ ✅ **已完成**：注册 `time_now`/`calculator` 内置工具 + seed `clock` agent，问时间即出 `tool_call/tool_result`（外加顺手修了 gateway binding/model 接缝 bug）。
- **B. 正经知识库工具**：等 retrieval WIP 收尾 + `APP_RETRIEVAL_ENABLED=true` + 给 agent 绑知识库，trace 出现 `knowledge_search` 调用。
- **C. Phase 2 外部工具 / MCP / handoff**：把 `agent_tools` 表 `source=external` 注册成可执行 handler；接 MCP；解析 `extra_json` 里的 policy；agent 间 handoff/delegation。
