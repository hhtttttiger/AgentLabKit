<!-- Parent: ../../AGENTS.md -->

# evaluation — Agent-native Testing & Evaluation

## Purpose

`evaluation` evaluates agent behavior against stable dataset examples and real Runtime outputs. It is not the owner of execution, Trace, or execution identity. Evaluators receive an `EvaluationContext` containing a `DatasetExample`, an `AgentRun`/`RunView`, and optional Trace spans.

```text
DatasetExample + AgentRun + Trace (when needed)
                    ↓
                Evaluator
                    ↓
             EvaluationResult
```

RAGAS, LLM judges, and external adapters are optional evaluator implementations. The core model is agent-native and deterministic-first.

## Responsibilities

- Define `DatasetExample`, `Expectation`, `Evaluator`, `EvaluationResult`, and `EvaluationRun` contracts.
- Keep stable `example_id` under Dataset ownership; `run_id` may differ for every execution.
- Run real targets through `RunExecutor`/Runtime adapters when evaluation requires execution.
- Obtain spans through `TraceProvider(trace_id)` rather than depending on observability storage internals.
- Compare baseline and candidate `EvaluationRun` objects only after validating dataset identity/version and evaluator specs.
- Replay historical input/context by requesting a new Runtime execution.

## Canonical result hierarchy

```text
EvaluationRun
    ↓
ExampleEvaluation[]
    ↓
EvaluationResult[]
```

The flat `results` property is a derived backward-compatibility view only. `EvaluationResult.passed`/score/label describe evaluator outcome. `PASS`, `FAIL`, and `SKIPPED` can all be successful evaluator executions; only an exception, runner error, or infrastructure failure makes `EvaluationRun` fail.

## Dataset and identity

Dataset owns `DatasetExample.example_id`. A baseline and candidate for the same case retain the same `example_id`, while their Runtime-owned `run_id` and `trace_id` differ. Never use `run_id` as stable dataset identity. `source_run_id` and `source_trace_id` are provenance fields, not replacements for `example_id`.

## RunExecutor and TraceProvider

A `RunExecutor` delegates real evaluation/replay execution to Runtime and returns its `RunView`/`AgentRun`. Evaluation and Replay must not hand-construct an `AgentRun`, generate IDs, or call Runtime internals. A trace-aware evaluator uses `TraceProvider(trace_id)` to obtain spans.

When replay configuration has no target, preserve the original Run target, including `agent_version`. Replay only supplies historical input/context, target, and metadata to `RunExecutor`; Runtime owns the new execution and identity.

## Deterministic-first evaluator order

Prefer tool-called/not-called, tool count, tool arguments, trajectory, max steps, latency, cost, and no-unhandled-error checks. LLM-as-a-judge, RAGAS, and other providers/adapters come after deterministic checks and must not redefine the execution model.

## Dependency rules

- Consume Run/Trace contracts; do not make Runtime depend on Evaluation.
- Keep provider-specific integrations behind evaluator protocols/adapters.
- Compare the same DatasetExample across comparable EvaluationRuns only.

## Testing expectations

Test PASS, FAIL, SKIPPED, and ERROR separately; a failed expectation is not a runner failure. Test dataset identity stability, TraceProvider injection, canonical result hierarchy, comparability validation, replay target/version preservation, new Runtime-owned IDs, and stable example IDs. Relevant tests include `test_contracts_v2.py`, `test_dataset.py`, `test_agent_native_evaluators.py`, `test_compare.py`, and `test_replay.py`.

## Key files

- `src/evaluation/contracts_v2.py` — v2 contracts and protocols.
- `src/evaluation/dataset.py` — DatasetEvaluationRunner and TraceProvider use.
- `src/evaluation/replay.py` — ReplayRunner and RunExecutor boundary.
- `src/evaluation/compare.py` — comparable EvaluationRun comparison.
