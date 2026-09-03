<!-- Parent: ../../AGENTS.md -->
# Runtime execution engine

此 subtree 实现核心 `AgentRuntime` execution paths（`run_turn`、`stream_turn` 和 workflow entrypoints）。Runtime 拥有 execution identity、lifecycle 和 semantic event emission；lower-level helpers 必须传递 supplied context，而不是创建无关 IDs。

- 将 preparation、guards、tool execution、loop 和 post-processing 保持为显式 collaborators。
- 每个 started execution 必须恰好产生一个 terminal event。
- 保持 streaming 遵循 public stream contract；internal events 不会自动成为 API events。
- Definition generation 后，workflow execution 是 deterministic，并复用 shared tool/sub-agent executors。
- 不要让 Runtime 依赖 Evaluation 或 backend modules。

Runtime 变更使用 `packages/agent_runtime/tests/` 下的相关 tests 验证，尤其是 lifecycle、event、streaming 和 architecture-invariant tests。参见 parent [agent_runtime instructions](../../../AGENTS.md) 和 [Execution Model v2](../../../../../docs/architecture/execution-model-v2.md)。
