# AgentLabKit Application

`packages/application` 包含 framework-neutral platform use cases。它协调 domain capabilities，但不拥有 Runtime facts、HTTP concerns 或 persistence schemas。

## 当前 use cases

- `ExecuteAgent`
- `ReplayRun`
- `CaptureRunAsDatasetExample`
- `EvaluateDataset`
- `CompareEvaluationRuns`

该 package 由 backend composition root 接入 production wiring。`ReplayRun` 和 evaluation 通过 `RunExecutor` 委托真实 execution；它们绝不构造 `AgentRun`、生成 IDs 或制造 events。Dataset storage 创建稳定的 `example_id`；source `run_id` 仅用于 provenance。

`EvaluateDataset` 负责 agent-target evaluation orchestration，`evaluation` package 负责 evaluator semantics 和 verdicts。legacy `rag_pipeline` target 保持使用现有 runner。`CompareEvaluationRuns` 按稳定的 dataset example identity 对齐 results，不执行 Runtime。

Application contracts 不是 HTTP DTOs。将 adapters 放在 `backend`，将 resource CRUD 放在 module services，并将长篇 ownership rules 放在 [`docs/architecture/`](../../docs/architecture/)。
