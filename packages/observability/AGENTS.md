<!-- Parent: ../../AGENTS.md -->

# observability

## 目的

Observability 观测 Runtime execution。它将 semantic `RuntimeEvent` facts projection 为用于查询和诊断的 `Trace` 与 `Span` records；不定义或执行 Run。

## 职责

- 通过 EventBus 或 `TraceProjector` 消费 `RuntimeEvent`。
- 保留 Runtime 提供的 `run_id`、`trace_id`、`span_id` 和 `parent_span_id`。
- 将 start/completion/failure events 关联为 spans，并在 Run terminal event 时结束一个 Trace。
- 安全降级地诊断 malformed、unknown、duplicate-start 和 orphan-completion events。

## Projector rules

Projectors **不得**生成 `run_id`、`trace_id`、`span_id` 或 `parent_span_id`，不得猜测 parents，也不得从 names/order 推断 operation identity。显式的 Runtime identity 始终优先。缺少 identity 是 malformed input，不是伪造 identity 的许可。

一个 operation 映射到一个 span identity。多个 semantic events 可以丰富同一个 span，例如 `GuardrailEvaluated` 后接 `GuardrailBlocked`，但不得创建第二个 span。`span_id` 在一个 Trace 内唯一。

`Trace` 是 `AgentRun` 的 Observability projection；`Run != Trace`。Run lifecycle 由 `agent_runtime` 拥有，projector 等待 `RunCompleted`、`RunFailed` 或 `RunCancelled` 来结束 root Trace。

## Dependency rules

- 消费 Runtime event contract；不要 import 或控制 Runtime internals。
- 不要依赖 Evaluation 或 Compare。
- 将 storage 和 HTTP concerns 保持在 `TraceStore`/module interfaces 后面。

## Testing expectations

覆盖 identity 与 parent preservation、one-span-per-operation、event enrichment、duplicate span IDs、orphan completions、malformed/unknown events、open-span finalization 和所有 terminal statuses。参见 `tests/test_projector.py` 和 `tests/test_span_processor.py`。

## 关键文件

- `src/observability/projector.py` — pure RuntimeEvent-to-Trace projection。
- `src/observability/contracts.py` — Trace/Span contracts。
- `src/observability/trace_store.py` — Trace persistence protocol。
