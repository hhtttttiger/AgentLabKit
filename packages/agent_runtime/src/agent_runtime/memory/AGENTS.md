<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-03 -->

# agent_runtime/memory

## Purpose
提供生产级记忆与上下文管理能力，在 pydantic-ai 调用层之前对 history 做 token-aware 裁剪、摘要压缩、消息优先级保护和可选的 session 持久化，确保长对话下 context window 不溢出、关键信息不丢失。

## 实施状态

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | Token-aware 截断、MessagePriority、ContextManager、AgentRuntime 集成 | ✅ 完成 |
| Phase 2 | GatewaySummarizer、摘要压缩、增量摘要 | ✅ 完成 |
| Phase 3 | SessionStore 协议 + InMemorySessionStore | ✅ 完成 |
| Phase 3 | PostgresSessionStore + migration | ❌ 待实施 |

## Key Files

| File | Description |
|------|-------------|
| `context_manager.py` | 核心入口：`ContextManager` + `ContextWindow` + `ContextWindowConfig`；实现 token-aware 裁剪与摘要触发 |
| `token_counter.py` | `TokenCounter` protocol + `TiktokenCounter`（默认）+ `ApproximateTokenCounter`（tiktoken 不可用时 fallback） |
| `summarizer.py` | `Summarizer` protocol + `GatewaySummarizer`：通过 llm_gateway 调用 LLM 生成对话摘要 |
| `message_priority.py` | `MessagePriority` 枚举（PINNED / NORMAL / LOW）及消息元数据标记/读取工具函数 |
| `session_store.py` | `SessionStore` protocol + `SessionSnapshot` + `InMemorySessionStore` |

## Public API

```python
# 核心数据类
ContextWindowConfig(max_total_tokens, reserve_for_response, reserve_for_system,
                    summarize_threshold_ratio, min_recent_messages, enable_summarization)
ContextWindow          # prepare_context() 的输出；.to_messages() 拼接为最终 history
SessionSnapshot        # session 快照；含 messages / summary / turn_count / total_tokens_consumed

# 核心类
ContextManager(config, token_counter, summarizer=None)
    .prepare_context(system_prompt, history, user_message) -> ContextWindow  # 主入口，async

GatewaySummarizer(gateway, model=None)
    .summarize(messages, context_hint=None) -> str

InMemorySessionStore()
    .load(session_id) / .save(session_id, snapshot) / .delete(session_id)

# 消息优先级工具
mark_message_priority(msg, priority)   # 写入 metadata["_priority"]
resolve_message_priority(msg)          # 读取，默认 NORMAL
is_pinned_message(msg) -> bool
is_summary_message(msg) -> bool

# Token 计数
TiktokenCounter(model="gpt-4o")
ApproximateTokenCounter()              # 字符数 / 4，无 tiktoken 依赖
create_default_token_counter(model)    # 自动选择实现
```

## For AI Agents

### Working In This Directory
- `ContextManager` 是纯预处理层，在 `AgentRuntime` 调用 pydantic-ai 之前运行，**不侵入 pydantic-ai 内部**。
- `memory.enabled=False`（默认）时，`AgentRuntime` 走原始 `_trim_history()` 路径，**零行为变化**；变更 ContextManager 逻辑前必须先验证此回归路径。
- 摘要消息以 `role=system`、`metadata[MEMORY_KIND_METADATA_KEY]=MEMORY_KIND_SUMMARY` 注入，解析时用 `is_summary_message()` 判断，不要用 role 直接匹配。
- `PostgresSessionStore` 尚未实现；如需持久化跨进程，优先按 `SessionStore` protocol 新增实现，不要修改 `InMemorySessionStore`。
- 增量摘要逻辑：新一轮压缩时，把上次摘要消息 + 超出预算的新消息一起送入 `GatewaySummarizer`，避免摘要信息丢失。

### Testing Requirements
- 变更后运行：`python3 -m pytest templates/python/agent_runtime/tests/test_memory.py`
- 回归测试：`python3 -m pytest templates/python/agent_runtime/tests/` （全套，含 memory.enabled=False 场景）

### Common Patterns
```python
# 启用 memory 的典型装配
from agent_runtime import ContextManager, ContextWindowConfig, create_default_token_counter

config = ContextWindowConfig(max_total_tokens=8000, enable_summarization=True)
counter = create_default_token_counter("gpt-4o")
summarizer = GatewaySummarizer(gateway_service)
ctx_mgr = ContextManager(config, counter, summarizer)

# 在 AgentRuntime 通过 create_agent_runtime(context_manager=ctx_mgr) 注入
```

## Dependencies

### Internal
- `agent_runtime.contracts.models` — `AgentMessage`, `AgentRole`
- `llm_gateway.core.service.GatewayService` — 摘要 LLM 调用（Phase 2）

### External
- `tiktoken>=0.8.0`（optional；不安装时 fallback 到 `ApproximateTokenCounter`）

## See Also
- [../AGENTS.md](../AGENTS.md)
- [计划文档](../../../../../../templates/plans/agent_plan/2026-04-02-agent-memory-context-plan.md)
