<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-03 -->

# agent_runtime/guardrails

## Purpose
提供可组合的输入/输出/工具调用安全 pipeline，作为 `AgentRuntime` 的前置/后置 middleware，拦截 prompt injection、PII 泄露、有害内容、恶意工具参数等风险，而不修改 pydantic-ai 的 agent loop 本体。

## 实施状态

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | `Guard`/`GuardResult`/`GuardsPipeline`、`PromptInjectionGuard`、`InputLengthGuard`、run_turn / stream_turn 输入链路集成 | ✅ 完成 |
| Phase 2 | `PiiMaskingGuard`、`ContentSafetyGuard`、streaming post_complete 输出守卫集成 | ✅ 完成 |
| Phase 3 | `ParameterGuard`、tool guard 在 run_turn / stream_turn 的统一执行链路、guard factory 扩展注册点 | ✅ 完成 |
| 待补齐 | 仓库级 `.NET` jailbreak smoke 强断言（`tests/agent/agent-jailbreak-smoke.ps1`） | ❌ 待实施 |

## Key Files

| File | Description |
|------|-------------|
| `contracts.py` | `Guard` protocol、`GuardVerdict`（PASS/MODIFY/BLOCK）、`GuardResult`、`GuardContext`、`GuardPipelineResult`、`GuardAuditCallback` |
| `pipeline.py` | `GuardsPipeline`：顺序执行 guard 列表，支持 MODIFY 链式改写、BLOCK 短路；同时作用于 input / output / tool 三条链路 |
| `factory.py` | `GuardRegistry`、`build_guards_pipeline(settings)`、`register_guard_factory(name, fn)` 扩展注册点 |
| `input/prompt_injection.py` | `PromptInjectionGuard`：关键词 + 启发式规则检测 prompt injection / jailbreak |
| `input/input_length.py` | `InputLengthGuard`：超长输入直接 BLOCK，防止 token 配额耗尽 |
| `output/pii_masking.py` | `PiiMaskingGuard`：正则脱敏电话/邮件/身份证等 PII（MODIFY 路径） |
| `output/content_safety.py` | `ContentSafetyGuard`：关键词黑名单 + 可配置严重度阈值；配置非法时构造即抛 ValueError |
| `tool/parameter_guard.py` | `ParameterGuard`：工具参数黑名单值检测，防止 LLM 传递恶意参数 |

## Public API

```python
# 核心协议与数据类
class GuardVerdict(str, Enum):
    PASS = "pass"; MODIFY = "modify"; BLOCK = "block"

Guard                          # protocol：async def check(ctx) -> GuardResult
GuardContext(user_message, session_id, agent_key, metadata)
GuardResult(verdict, modified_text=None, block_reason=None, guard_name=None)
GuardPipelineResult            # pipeline 执行汇总

# Pipeline
GuardsPipeline(input_guards, output_guards, tool_guards, audit_callback=None)
    .run_input(ctx) -> GuardPipelineResult
    .run_output(ctx) -> GuardPipelineResult
    .run_tool(ctx)  -> GuardPipelineResult

# Factory & 扩展注册
build_guards_pipeline(settings: GuardrailsSettings) -> GuardsPipeline
register_guard_factory(name, factory_fn)     # 注册自定义 guard 工厂

# 内置 Guards（可直接实例化）
PromptInjectionGuard(patterns=None)
InputLengthGuard(max_chars=4000)
PiiMaskingGuard(patterns=None)
ContentSafetyGuard(blocked_keywords, severity_threshold="medium")
ParameterGuard(blocked_values=None)
```

## For AI Agents

### Working In This Directory
- Guardrails 是纯 middleware 层，**不修改 pydantic-ai agent loop**；`run_turn()` 和 `stream_turn()` 各自在调用 pydantic-ai 前运行 input guards，调用完成后运行 output guards。
- `GuardVerdict.MODIFY` 路径：guard 返回修改后的文本，pipeline 将其传给下一个 guard，最终替换原始文本；每个 MODIFY guard 都应写入 `modified_text`，不得置 None。
- `GuardVerdict.BLOCK` 路径：立即短路，返回预定义安全回复；`block_reason` 必须非空，这是外部可观测的契约（见回归测试 `block_reason contract`）。
- 新增 guard 时优先使用 `register_guard_factory()` 注册，而不是直接在 `factory.py` 里硬编码。
- `ContentSafetyGuard` 配置非法时在构造期抛 `ValueError`，不要在 `check()` 里抛；这是已有测试覆盖的契约，不得改动。
- jailbreak smoke 测试（`tests/agent/agent-jailbreak-smoke.ps1`）当前仅验证"不崩溃"；待 `.NET` 侧响应契约稳定后需补"攻击确实被拦截"的强断言，届时需同步更新此文件。

### Testing Requirements
- 变更后运行：`python3 -m pytest templates/python/agent_runtime/tests/test_guardrails.py`
- 全套回归：`python3 -m pytest templates/python/agent_runtime/tests/`

### Common Patterns
```python
from agent_runtime import GuardrailsSettings, build_guards_pipeline

settings = GuardrailsSettings(
    enable_prompt_injection_guard=True,
    enable_input_length_guard=True,
    max_input_chars=4000,
    enable_pii_masking=True,
    enable_content_safety=True,
)
pipeline = build_guards_pipeline(settings)
# 在 AgentRuntime 通过 create_agent_runtime(guards_pipeline=pipeline) 注入

# 注册自定义 guard
register_guard_factory("my_custom_guard", lambda cfg: MyCustomGuard(cfg))
```

## Dependencies

### Internal
- `agent_runtime.config.guardrails.GuardrailsSettings`
- `agent_runtime.contracts.models.AgentMessage`

### External
- 无额外外部依赖（所有内置 guard 使用标准库正则）

## See Also
- [../AGENTS.md](../AGENTS.md)
- [计划文档](../../../../../../templates/plans/agent_plan/2026-04-02-agent-guardrails-plan.md)
