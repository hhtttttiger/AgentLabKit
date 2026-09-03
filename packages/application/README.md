# AgentLabKit Application

`packages/application` contains framework-neutral platform use cases. It coordinates domain capabilities without owning Runtime facts, HTTP concerns, or persistence schemas.

## Current use cases

- `ExecuteAgent`
- `ReplayRun`
- `CaptureRunAsDatasetExample`
- `EvaluateDataset`
- `CompareEvaluationRuns`

The package is production-wired by the backend composition root. `ReplayRun` and evaluation delegate real execution through `RunExecutor`; they never construct `AgentRun`, generate IDs, or manufacture events. Dataset storage creates stable `example_id`; a source `run_id` is provenance only.

`EvaluateDataset` owns agent-target evaluation orchestration while the `evaluation` package owns evaluator semantics and verdicts. The legacy `rag_pipeline` target remains on its existing runner. `CompareEvaluationRuns` aligns results by stable dataset example identity and does not execute Runtime.

Application contracts are not HTTP DTOs. Keep adapters in `backend`, resource CRUD in module services, and long-form ownership rules in [`docs/architecture/`](../../docs/architecture/).
