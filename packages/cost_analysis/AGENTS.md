<!-- Parent: ../../AGENTS.md -->

# cost_analysis

## Purpose

Cost analysis is a projection of execution facts. It records and aggregates usage/cost information without executing agents or reconstructing Runs.

## Responsibilities

```text
LLMCallCompleted / LLMCallFailed
              ↓
        CostProjector
              ↓
         CostRecord
```

`CostProjector` consumes RuntimeEvents and publishes one cost record for each relevant LLM operation, including Runtime identity, model/provider, usage, timestamps, and errors. Aggregators and budget managers query these records and manage budget policy.

## Ownership and boundaries

`run_id`, `trace_id`, and `span_id` on a `CostRecord` must come from the RuntimeEvent. Cost analysis must not generate IDs, infer spans, or use database request-log ordering as execution identity. It does not own `AgentRun` or `Trace`.

The package may aggregate by run, agent, workflow, model, or time period, but aggregation must preserve the source execution identity. It must not depend on Evaluation or make evaluation decisions.

## Dependency rules

- Consume RuntimeEvent contracts through the projector boundary.
- Keep Runtime and LLM Gateway implementations out of the cost projection layer.
- Database persistence and HTTP routes remain behind package interfaces and backend adapters.

## Testing expectations

Verify `LLMCallCompleted` and failed calls preserve all identity and usage fields, produce correct timestamps, and do not fabricate missing execution identity. Also test aggregation, budgets, alerts, and malformed events. See `tests/test_projector.py` and `tests/test_contracts.py`.
