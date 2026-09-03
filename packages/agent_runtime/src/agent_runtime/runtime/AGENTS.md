# Runtime execution engine

This subtree implements the core `AgentRuntime` execution paths (`run_turn`, `stream_turn`, and workflow entrypoints). Runtime owns execution identity, lifecycle, and semantic event emission; lower-level helpers must propagate the supplied context rather than create unrelated IDs.

- Keep preparation, guards, tool execution, loop, and post-processing as explicit collaborators.
- Preserve exactly one terminal event for every started execution.
- Keep streaming on the public stream contract; internal events are not automatically API events.
- Workflow execution is deterministic after definition generation and reuses the shared tool/sub-agent executors.
- Do not make Runtime depend on Evaluation or backend modules.

Verify runtime changes with the relevant tests under `packages/agent_runtime/tests/`, especially lifecycle, event, streaming, and architecture-invariant tests. See the parent [agent_runtime instructions](../../../AGENTS.md) and [Execution Model v2](../../../../../docs/architecture/execution-model-v2.md).