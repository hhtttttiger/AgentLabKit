<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-03 -->

# agent_runtime/config

## Purpose
集中定义 `agent_runtime` 的所有运行时配置模型，通过 pydantic-settings 从环境变量加载，支持嵌套配置（memory / guardrails），是所有模块默认行为的单一配置入口。

## Key Files

| File | Description |
|------|-------------|
| `agent.py` | `AgentSettings`：顶层配置类，env prefix `AGENT_RUNTIME_`；含 agent 基础参数、memory 子配置、guardrails 子配置 |
| `memory.py` | `MemorySettings`：控制 memory 模块开关与参数；`enabled=False` 时记忆层完全旁路 |
| `guardrails.py` | `GuardrailsSettings`：控制各 guard 开关与参数；`enabled=False` 时 guardrails pipeline 完全旁路 |

## Public API

```python
class AgentSettings(BaseSettings):
    # 环境变量前缀: AGENT_RUNTIME_（嵌套分隔符: __）
    agent_name: str = "customer_support_agent"
    default_model: str = "gpt-4.1-mini"
    default_system_prompt: str = "..."
    max_history_messages: int = 20
    max_output_tokens: int | None = 800
    temperature: float | None = 0.2
    enable_knowledge_tool: bool = True
    knowledge_top_k: int = 5
    enable_handoff_policy: bool = True
    default_handoff_message: str = "..."
    model_retries: int = 1
    output_retries: int = 1
    prompt_sections: tuple[str, ...] = ("role", "tooling", "handoff")
    memory: MemorySettings
    guardrails: GuardrailsSettings

class MemorySettings(BaseModel):
    enabled: bool = False                        # False = 走旧 _trim_history() 路径
    max_total_tokens: int = 8000
    reserve_for_response: int = 1500
    reserve_for_system: int = 1500
    summarize_threshold_ratio: float = 0.8
    min_recent_messages: int = 4
    enable_summarization: bool = True
    summarization_model: str | None = None       # None = 使用 agent 同模型
    tokenizer_model: str = "gpt-4o"
    persist_sessions: bool = False               # True = 启用 SessionStore load/save

class GuardrailsSettings(BaseModel):
    enabled: bool = True
    enable_prompt_injection_guard: bool = True
    enable_input_length_guard: bool = True
    max_input_chars: int = 4000
    enable_pii_masking: bool = False
    enable_content_safety: bool = False
    content_safety_keywords: list[str] = []
    enable_parameter_guard: bool = False
```

## For AI Agents

### Working In This Directory
- 所有新增配置字段必须有**显式默认值**，确保现有部署零改动即可升级。
- 嵌套配置通过 `AGENT_RUNTIME_MEMORY__ENABLED=true` 形式的环境变量覆盖。
- `memory.enabled` 和 `guardrails.enabled` 是各自模块的主开关；功能开关（如 `enable_pii_masking`）仅在主开关打开时生效。
- 修改字段类型或默认值前，先检查 `tests/test_module.py` 中的配置加载测试。
- `prompt_sections` 控制 `build_system_prompt()` 的段落组合，修改默认值会影响所有 agent 的系统提示结构。

### Testing Requirements
- 变更后运行：`python3 -m pytest templates/python/agent_runtime/tests/test_module.py`

## Dependencies

### External
- `pydantic>=2.0`
- `pydantic-settings>=2.0`

## See Also
- [../AGENTS.md](../AGENTS.md)
