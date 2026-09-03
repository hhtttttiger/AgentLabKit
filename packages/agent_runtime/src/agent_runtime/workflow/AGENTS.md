# Runtime workflows

This subtree implements deterministic multi-step workflow execution. `WorkflowGenerator` may use the LLM to create a definition; `WorkflowEngine` executes that definition without making new LLM routing decisions.

- Reuse the shared `ToolExecutor` and `SubAgentExecutor`; do not duplicate tool or Agent Loop behavior.
- Pass step data through explicit `InputRef` values (`$user_input`, `$steps.*`, `$const:*`).
- Preserve condition branching, failure policies, human-gate checkpoints, resume behavior, and public stream events.
- Keep generation and execution separate, and keep workflow code independent of backend transport.

Run the workflow tests under `packages/agent_runtime/tests/` after changes. See the parent [agent_runtime instructions](../../../AGENTS.md).