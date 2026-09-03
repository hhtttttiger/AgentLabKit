<!-- Parent: ../../AGENTS.md -->
# Agent Runtime

`agent_runtime` owns real Agent execution and in-process workflow execution. It creates `ExecutionContext`, owns `run_id`/`trace_id`/span identity and lifecycle, emits semantic `RuntimeEvent` facts, and returns `AgentRun`.

## Rules

- Propagate the supplied execution context; lower-level helpers must not create unrelated IDs.
- Emit exactly one terminal event for every `RunStarted`, including streaming, workflow, handoff, delegation, cancellation, and guardrail-blocked paths.
- A guardrail block is normally a valid business outcome, not a Runtime crash.
- Keep Runtime independent of Evaluation, Compare, backend, and observability implementations.
- Replay and Evaluation use `RunExecutor`; they do not construct `AgentRun` or call Runtime internals.
- Add semantic events for new capabilities rather than requiring consumers to infer behavior from logs.

## Key paths

- `src/agent_runtime/contracts/` — execution and turn contracts.
- `src/agent_runtime/events_v2.py` — RuntimeEvent facts.
- `src/agent_runtime/runtime/` — execution engine and loop.
- `src/agent_runtime/tools/`, `guardrails/`, `memory/`, `workflow/` — local execution capabilities.

Run targeted tests under `packages/agent_runtime/tests/`; lifecycle and architecture changes also need the relevant cross-package tests. See [Execution Model v2](../../docs/architecture/execution-model-v2.md).