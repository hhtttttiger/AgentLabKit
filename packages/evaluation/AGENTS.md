# Evaluation

`evaluation` 使用稳定的 DatasetExamples 和真实 Runtime outputs 评判 agent behavior。它负责 evaluator contracts、results 和 EvaluationRun semantics，不负责 execution、Trace 或 execution identity。

- Dataset 拥有稳定的 `example_id`；不同 executions 的 `run_id` 和 `trace_id` 不同，且永远不是 dataset identity。
- 真实 replay/evaluation execution 通过 `RunExecutor`；这里不要构造 `AgentRun` 或调用 Runtime internals。
- 通过 `TraceProvider` 获取 optional spans，不要访问 observability storage internals。
- `PASS`、`FAIL` 和 `SKIPPED` 是 evaluator outcomes。Evaluator/runner/infrastructure errors 属于 EvaluationRun failures。
- 优先使用 deterministic evaluators；provider integrations 是 adapters。
- 只比较兼容的 EvaluationRuns，并按 `DatasetExample.example_id` 对齐，绝不按 position 或 input text 对齐。

参见 [Execution Model v2](../../docs/architecture/execution-model-v2.md)，并运行 `packages/evaluation/tests/` 下的相关 tests。
