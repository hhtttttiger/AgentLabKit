<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-07-06 -->

# agent_runtime/workflow

## Purpose
提供确定性多步骤流程编排引擎。用户描述意图后，LLM 根据 agent 绑定的 tools/MCP/skills 生成一条只读流程定义（WorkflowDef），引擎按步骤确定性执行，支持工具调用、子 Agent 委托、人工确认暂停、条件分支等步骤类型。

核心理念：**编排是 LLM 的能力（生成），不是用户的能力（拖拉拽）；执行是引擎的能力（确定性），不是 LLM 的能力（实时决策）。**

## 实施状态

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | 数据契约（WorkflowDef/StepDef/InputRef/FailurePolicy）、WorkflowEngine 串行执行、StepExecutor（tool/agent/human_gate/condition）、InMemoryStateStore、42 个单元测试 | ✅ 完成 |
| Phase 2 | 条件分支深度优化、Human gate 暂停/恢复、checkpoint 持久化、流式事件（WorkflowStreamEvent）、stream_workflow/resume_workflow | ✅ 完成 |
| Phase 3 | WorkflowGenerator — LLM 生成流程定义、生成 prompt 模板、校验逻辑、集成测试 | ✅ 完成 |

## Key Files

| File | Description |
|------|-------------|
| `contracts.py` | 所有数据契约：`WorkflowDef`（流程定义）、`StepDef`（步骤定义）、`InputRef`（输入引用）、`FailurePolicy`（失败策略）、`StepResult`/`WorkflowResult`（执行结果）、`WorkflowStreamEvent`（流式事件）、`WorkflowRequest`（执行请求） |
| `engine.py` | `WorkflowEngine`：确定性流程执行引擎，支持 `run_workflow()`（阻塞）、`stream_workflow()`（流式）、`resume_workflow()`（从 human gate 恢复） |
| `step_executor.py` | `StepExecutor`：步骤执行分发器，根据 `step_type` 调用 `ToolExecutor`（tool）、`SubAgentExecutor`（agent）、条件求值（condition）、暂停（human_gate） |
| `state_store.py` | `WorkflowStateStore` protocol + `InMemoryWorkflowStateStore` 实现；`WorkflowCheckpoint` 用于 human gate 暂停时的状态持久化 |
| `generator.py` | `WorkflowGenerator`：LLM 驱动的流程生成器，根据用户意图 + agent 能力生成 `WorkflowDef`；包含 prompt 构建、响应解析、流程校验 |
| `__init__.py` | 统一导出所有公开类型 |

## Public API

```python
# === 数据契约 ===

# 输入引用（三种来源）
InputRef("$user_input")                    # 用户原始输入
InputRef("$steps.lookup.order_id")         # 上游步骤输出
InputRef("$const:default_value")           # 常量值
ref.resolve(context_vars) -> Any           # 解析引用

# 失败策略
FailurePolicy(on_failure="fail")           # 终止（默认）
FailurePolicy(on_failure="retry", max_retries=3, retry_delay_seconds=1.0)  # 重试
FailurePolicy(on_failure="skip")           # 跳过

# 步骤定义
StepDef(
    step_id="lookup_order",
    step_type="tool",                      # tool | agent | human_gate | condition
    display_name="查询订单",
    tool_name="order_lookup",              # tool 类型必填
    tool_arguments={"order_id": InputRef("$user_input")},
    failure_policy=FailurePolicy(on_failure="retry"),
)

# 流程定义
WorkflowDef(
    workflow_id="wf-001",
    agent_key="customer_support",
    version=1,
    steps=(step_1, step_2, step_3),
)
workflow.get_step("step_id") -> StepDef | None
workflow.step_index("step_id") -> int

# === 执行引擎 ===

engine = WorkflowEngine(step_executor, state_store, event_bus=None)
result = await engine.run_workflow(workflow, user_input, context)
async for event in engine.stream_workflow(workflow, user_input, context): ...
result = await engine.resume_workflow(workflow, human_response, context)

# === 步骤执行器 ===

step_executor = StepExecutor(tool_executor, tool_registry, sub_agent_executor)
result = await step_executor.execute_step(step, resolved_input, context)

# === 状态持久化 ===

store = InMemoryWorkflowStateStore()
await store.save_checkpoint(checkpoint)
checkpoint = await store.load_checkpoint(workflow_id)
await store.clear_checkpoint(workflow_id)

# === 流程生成器 ===

from agent_runtime.workflow import WorkflowGenerator, WorkflowValidationError

generator = WorkflowGenerator(gateway_service, default_model="gpt-4")
try:
    workflow = await generator.generate(
        agent_definition=agent_def,
        user_intent="用户想要退款订单 #12345",
        max_steps=10,
        metadata={"source": "user_request"},
    )
except WorkflowValidationError as e:
    print(f"Validation failed: {e.errors}")
```

## For AI Agents

### Working In This Directory
- **与 pi 的解耦**：workflow 模块不修改 `runtime/loop.py`（pi 的 agent-loop.ts 转写）。pi 更新时只需同步 loop.py，workflow 不受影响。
- **复用现有执行器**：tool 步骤复用 `ToolExecutor`，agent 步骤复用 `SubAgentExecutor`，不要重新实现工具调用或 Agent Loop 逻辑。
- **确定性执行**：WorkflowEngine 在执行过程中不做 LLM 决策（除了 agent 类型步骤内部的 Agent Loop）。所有分支由 condition 步骤的表达式求值决定。
- **InputRef 解析**：所有步骤输入通过 `InputRef` 显式映射，不要隐式传递上下文。`$user_input`、`$steps.<id>.<key>`、`$const:<value>` 是三种标准来源。
- **条件分支**：condition 步骤通过 `condition_expr` 求值决定跳转目标。表达式格式为 `$steps.<id>.<key> <op> <value>`，支持 `==`、`!=`、`>`、`<`、`>=`、`<=`。
- **Human gate**：返回 `status="waiting_human"` 时引擎暂停，通过 `resume_workflow()` 恢复。checkpoint 持久化由 `WorkflowStateStore` 负责。
- **WorkflowGenerator**：LLM 驱动的流程生成器。给定用户意图 + agent 能力（tools/MCP/skills），生成确定性 `WorkflowDef`。生成和执行完全分离——生成器调用 LLM 创建流程定义，引擎按定义确定性执行。

### Testing Requirements
```bash
# 运行 workflow 单元测试
python3 -m pytest packages/agent_runtime/tests/test_workflow.py

# 运行 workflow 集成测试（Generator）
python3 -m pytest packages/agent_runtime/tests/test_workflow_integration.py

# 全套回归
python3 -m pytest packages/agent_runtime/tests/
```

### Common Patterns

```python
from agent_runtime.workflow import (
    WorkflowDef, StepDef, InputRef, FailurePolicy,
    WorkflowEngine, StepExecutor, InMemoryWorkflowStateStore,
)

# 构造一个退款流程
workflow = WorkflowDef(
    workflow_id="wf-refund-001",
    agent_key="customer_support",
    version=1,
    steps=(
        StepDef(
            step_id="lookup_order",
            step_type="tool",
            display_name="查询订单",
            tool_name="order_lookup",
            tool_arguments={"order_id": InputRef("$user_input")},
        ),
        StepDef(
            step_id="check_eligible",
            step_type="condition",
            display_name="检查退款资格",
            condition_expr="$steps.lookup_order.eligible == true",
            condition_true_step="confirm_refund",
            condition_false_step="reject_refund",
        ),
        StepDef(
            step_id="confirm_refund",
            step_type="human_gate",
            display_name="人工确认退款",
            gate_prompt="订单金额 {amount}，确认退款？",
            gate_options=("确认", "取消"),
        ),
        StepDef(
            step_id="execute_refund",
            step_type="tool",
            display_name="执行退款",
            tool_name="refund_execute",
            tool_arguments={
                "order_id": InputRef("$steps.lookup_order.order_id"),
            },
        ),
        StepDef(
            step_id="reject_refund",
            step_type="tool",
            display_name="拒绝退款",
            tool_name="send_message",
            tool_arguments={
                "message": InputRef("$const:抱歉，该订单不符合退款条件。"),
            },
        ),
    ),
)

# 执行
engine = WorkflowEngine(step_executor, InMemoryWorkflowStateStore())
result = await engine.run_workflow(workflow, "ORDER-12345", context)
```

## Dependencies

### Internal
- `agent_runtime.tools.executor.ToolExecutor` — tool 步骤执行
- `agent_runtime.tools.registry.DynamicToolRegistry` — 工具查找
- `agent_runtime.orchestration.sub_agent_executor.SubAgentExecutor` — agent 步骤执行
- `agent_runtime.tools.contracts.ToolExecutionContext` — 执行上下文
- `agent_runtime.contracts.models.ToolExecutionRecord` — 工具事件记录
- `agent_runtime.event_bus.EventBus` — 生命周期事件发射
- `agent_runtime.definition.models.AgentDefinitionSnapshot` — 流程定义挂载点、Generator 的输入

### External
- `llm_gateway.GatewayProtocol` — Generator 调用 LLM 生成流程定义
- `llm_gateway.TextGenerateRequest` — LLM 请求模型
- `llm_gateway.UsageInfo` — token 用量统计

## See Also
- [../AGENTS.md](../AGENTS.md)
- [../orchestration/](../orchestration/) — 现有单跳 Handoff/Delegation 编排
- [../tools/](../tools/) — 工具体系（ToolExecutor、DynamicToolRegistry）
