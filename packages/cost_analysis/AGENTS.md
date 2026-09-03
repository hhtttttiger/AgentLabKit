<!-- Parent: ../../AGENTS.md -->

# cost_analysis

## 目的

Cost analysis 是 execution facts 的 projection。它记录并聚合 usage/cost information，不执行 agents，也不重建 Runs。

## 职责

```text
LLMCallCompleted / LLMCallFailed
              ↓
        CostProjector
              ↓
         CostRecord
```

`CostProjector` 消费 RuntimeEvents，并为每个相关 LLM operation 发布一条 cost record，其中包括 Runtime identity、model/provider、usage、timestamps 和 errors。Aggregators 和 budget managers 查询这些 records 并管理 budget policy。

## Ownership 和边界

`CostRecord` 中的 `run_id`、`trace_id` 和 `span_id` 必须来自 RuntimeEvent。Cost analysis 不得生成 IDs、推断 spans，或使用 database request-log ordering 作为 execution identity。它不拥有 `AgentRun` 或 `Trace`。

Package 可以按 run、agent、workflow、model 或 time period 聚合，但聚合必须保留 source execution identity。它不得依赖 Evaluation 或作出 evaluation decisions。

## Dependency rules

- 通过 projector boundary 消费 RuntimeEvent contracts。
- 不要将 Runtime 和 LLM Gateway implementations 放入 cost projection layer。
- Database persistence 和 HTTP routes 保持在 package interfaces 与 backend adapters 后面。

## Testing expectations

验证 `LLMCallCompleted` 和 failed calls 保留全部 identity 与 usage fields，产生正确 timestamps，并且不伪造缺失的 execution identity。同时测试 aggregation、budgets、alerts 和 malformed events。参见 `tests/test_projector.py` 和 `tests/test_contracts.py`。
