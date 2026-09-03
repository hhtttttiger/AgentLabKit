<!-- Parent: ../../AGENTS.md -->
# Agent Runtime

`agent_runtime` 拥有真实 Agent execution 和进程内 workflow execution。它创建 `ExecutionContext`，拥有 `run_id`/`trace_id`/span identity 与 lifecycle，发出语义化 `RuntimeEvent` facts，并返回 `AgentRun`。

## 规则

- 传递 supplied execution context；lower-level helpers 不得创建无关 IDs。
- 每个 `RunStarted` 必须恰好发出一个 terminal event，包括 streaming、workflow、handoff、delegation、cancellation 和 guardrail-blocked paths。
- guardrail block 通常是有效的 business outcome，不是 Runtime crash。
- 保持 Runtime 独立于 Evaluation、Compare、backend 和 observability implementations。
- Replay 和 Evaluation 使用 `RunExecutor`；不得构造 `AgentRun` 或调用 Runtime internals。
- 为新能力增加 semantic events，不要要求 consumers 从 logs 推断行为。

## 关键路径

- `src/agent_runtime/contracts/` — execution 和 turn contracts。
- `src/agent_runtime/events_v2.py` — RuntimeEvent facts.
- `src/agent_runtime/runtime/` — execution engine 和 loop。
- `src/agent_runtime/tools/`、`guardrails/`、`memory/`、`workflow/` — local execution capabilities。

在 `packages/agent_runtime/tests/` 下运行 targeted tests；lifecycle 和 architecture 变更还需要相关 cross-package tests。参见 [Execution Model v2](../../docs/architecture/execution-model-v2.md)。