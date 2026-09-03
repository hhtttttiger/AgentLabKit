<!-- Parent: ../../AGENTS.md -->
# Runtime workflows

此 subtree 实现 deterministic multi-step workflow execution。`WorkflowGenerator` 可以使用 LLM 创建 definition；`WorkflowEngine` 执行该 definition，不作出新的 LLM routing decisions。

- 复用 shared `ToolExecutor` 和 `SubAgentExecutor`；不要重复实现 tool 或 Agent Loop behavior。
- 通过显式 `InputRef` values（`$user_input`、`$steps.*`、`$const:*`）传递 step data。
- 保留 condition branching、failure policies、human-gate checkpoints、resume behavior 和 public stream events。
- 分离 generation 与 execution，并保持 workflow code 独立于 backend transport。

变更后运行 `packages/agent_runtime/tests/` 下的 workflow tests。参见 parent [agent_runtime instructions](../../../AGENTS.md)。
