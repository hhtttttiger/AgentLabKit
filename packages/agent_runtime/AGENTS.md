<!-- Parent: ../../AGENTS.md -->

# agent_runtime

## Purpose

`agent_runtime` is the execution owner and in-process Agent engine. It runs agents and workflows through the LLM Gateway, tools, guardrails, handoffs, delegation, and streaming paths.

## Responsibilities

- Create and carry an `ExecutionContext` for each real execution.
- Own `run_id`, `trace_id`, `root_span_id`, target, timestamps, and execution metadata.
- Emit semantic `RuntimeEvent` facts for Run, Agent, Turn, LLM, Tool, Retrieval, Guardrail, Handoff, Delegation, and Workflow activity.
- Return an `AgentRun` for every real Runtime execution.
- Emit exactly one terminal event: `RunCompleted`, `RunFailed`, or `RunCancelled`.

## Architecture and ownership

`ExecutionContext` is the identity source. `AgentRuntime.run()` creates the execution boundary and `run_turn()`/streaming/workflow paths use the supplied context when one exists. Lower-level loop, LLM, tool, guardrail, handoff, and delegation code propagates identity; it must not create unrelated IDs.

`AgentRun` represents a real Runtime execution. It contains the input/output, target, status, usage, lifecycle timestamps, and execution metadata. It does not own Trace spans. Observability and cost packages consume the RuntimeEvents emitted by this package.

Runtime creates operation span identities and supplies `span_id`/`parent_span_id` on events. Multiple semantic events can describe one operation (for example `GuardrailEvaluated` and `GuardrailBlocked`); downstream projectors correlate them using the explicit identity.

## Dependency rules

- `agent_runtime` may depend on execution contracts and `llm_gateway`.
- Observability and cost analysis consume events without Runtime importing their implementations.
- Runtime must not depend on Evaluation or Compare.
- All public APIs are exported from `src/agent_runtime/__init__.py`.
- Replay and evaluation adapters call Runtime through `RunExecutor`; they do not call Runtime internals or construct `AgentRun`.

## Invariants

- `Run != Trace`: Run is the business execution boundary; Trace is an observability projection.
- Every `RunStarted` has exactly one terminal event, including success, failure, cancellation, streaming, workflow, handoff, delegation, and guardrail-blocked paths.
- Cancellation emits `RunCancelled`; exceptions emit `RunFailed`.
- A guardrail block is normally a valid business outcome, not a Runtime crash. The Run still terminates.
- Runtime is the sole creator of execution identity. `run()` and `run_turn()` must share an injected context rather than create unrelated identities.
- Add semantic events when adding runtime capabilities; do not require consumers to infer behavior from generic logs.

## Testing expectations

Test the complete event lifecycle, not only isolated helpers: success, failure, cancellation, guardrail block, streaming, workflow, handoff, and delegation. Verify identity propagation, exactly-one-terminal behavior, and event/span correlation. Relevant tests include `test_agent_run.py`, `test_run_method.py`, `test_events_v2.py`, `test_execution_model_acceptance.py`, and `test_architecture_invariants.py`.

## Key files

- `src/agent_runtime/contracts/run.py` — `ExecutionContext`, `AgentRun`, targets, status, and usage.
- `src/agent_runtime/events_v2.py` — semantic `RuntimeEvent` contracts.
- `src/agent_runtime/runtime/engine.py` — Runtime execution and lifecycle emission.
- `src/agent_runtime/runtime/loop.py` — Agent loop and operation events.
- `src/agent_runtime/workflow/` — deterministic workflow execution.
