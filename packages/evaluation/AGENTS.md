# Evaluation

`evaluation` judges agent behavior using stable DatasetExamples and real Runtime outputs. It owns evaluator contracts, results, and EvaluationRun semantics—not execution, Trace, or execution identity.

- Dataset owns stable `example_id`; `run_id` and `trace_id` differ across executions and are never dataset identity.
- Real replay/evaluation execution goes through `RunExecutor`; never construct `AgentRun` or call Runtime internals here.
- Obtain optional spans through `TraceProvider`, not observability storage internals.
- `PASS`, `FAIL`, and `SKIPPED` are evaluator outcomes. Evaluator/runner/infrastructure errors are EvaluationRun failures.
- Prefer deterministic evaluators; provider integrations are adapters.
- Compare only compatible EvaluationRuns and align by `DatasetExample.example_id`, never by position or input text.

See [Execution Model v2](../../docs/architecture/execution-model-v2.md) and run the relevant tests under `packages/evaluation/tests/`.