<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-03 -->

# agent_runtime/contracts

## Purpose
定义 `agent_runtime` 对外暴露的核心数据契约：请求/响应模型、枚举、流式事件类型等；是 `agent_service`（传输层）与 `agent_runtime`（编排层）之间的稳定边界。

## Key Files

| File | Description |
|------|-------------|
| `models.py` | 所有契约数据类（Pydantic model）；`AgentTurnRequest`、`AgentTurnResult`、`AgentTurnStreamEvent` 是主要 I/O 契约 |

## Public API

```python
# 枚举
class AgentRole(str, Enum):
    USER = "user"; ASSISTANT = "assistant"; SYSTEM = "system"; TOOL = "tool"

class AgentAction(str, Enum):
    REPLY = "reply"; HANDOFF = "handoff"

# 核心消息结构
AgentMessage(role: AgentRole, content: str, name=None, metadata={})
KnowledgeChunk(content, source=None, score=None)
ToolExecutionRecord(tool_name, input_args, output, error=None, duration_ms=None)

# 请求/响应
AgentTurnRequest(
    session_id: str,
    user_message: str,
    history: list[AgentMessage] = [],
    agent_key: str | None = None,   # definition-aware 路由
    metadata: dict = {},
)
AgentTurnResult(
    reply: str,
    action: AgentAction,
    handoff: HandoffDecision | None,
    knowledge_chunks: list[KnowledgeChunk],
    tool_records: list[ToolExecutionRecord],
    session_state: AgentSessionState,
    metadata: dict,
)

# 流式事件
AgentTurnStreamEvent(
    event_type: str,   # "token" | "done" | "error"
    token: str | None,
    result: AgentTurnResult | None,
    error: AgentErrorDetail | None,
)

# 辅助
HandoffDecision(target: str, reason: str)
AgentDecision(action: AgentAction, handoff: HandoffDecision | None)
AgentSessionState(session_id, turn_count, metadata)
AgentErrorDetail(code: str, message: str, detail=None)
```

## For AI Agents

### Working In This Directory
- 这是 `agent_service` ↔ `agent_runtime` 的**稳定边界**；修改字段（尤其是 `AgentTurnRequest` / `AgentTurnResult`）前，需同步检查 `agent_service` 的传输层映射（HTTP/gRPC DTO）。
- 不要在此层添加业务逻辑；所有字段保持为纯数据（Pydantic model / dataclass）。
- `AgentTurnResult.metadata` 是非结构化扩展字段；memory 模块通过 `_context_tokens_used` 等 key 透传统计信息，消费方通过 key 约定读取，无需修改模型。
- `AgentMessage.metadata` 用于内部标记（priority、memory_kind），不对外传输；`agent_service` 层不应透传 metadata 给 client。
- `AgentTurnRequest.agent_key` 是 definition-aware 路由的主入参；为 None 时走 `AgentSettings` 默认配置。

### Testing Requirements
- 契约变更需同时检查：`test_runtime.py`（end-to-end）、`test_module.py`（module assembly）

## Dependencies

### External
- `pydantic>=2.0`

## See Also
- [../AGENTS.md](../AGENTS.md)
