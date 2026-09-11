# Agent Core Independence

This document defines the dependency guardrails for the Agent Runtime
subsystem. It protects the Agent Core's ability to evolve independently
without moving files or changing the Execution Model v2 contracts.

## Agent Core

Agent Core is the smallest execution algorithm that answers:

> Given state, a model, and tools, how does one agent execution progress?

The protected core surface is the agent loop, agent messages and state, loop
configuration/context, the LLM interaction abstraction, the tool execution
callback/protocol, cancellation, core streaming updates, and core lifecycle
primitives. Core code may depend on protocols and primitives. It must not
depend on platform implementations.

The current core-module allowlist is intentionally explicit rather than based
on physical directories:

- `agent_runtime.runtime.loop`
- `agent_runtime.runtime.llm_adapter`
- `agent_runtime.runtime.cancel`
- `agent_runtime.state`
- `agent_runtime.contracts.models`

This is a logical boundary, not a package-split plan.

## Runtime Harness and capabilities

`AgentRuntime` is the Runtime Harness. It prepares a turn, resolves an agent
definition, injects skills/guards/context, invokes Core, and coordinates
handoff, post-processing, memory, sessions, and persistence.

Workflow, MCP, voice, guardrails, skills, long-term memory, and multi-agent
orchestration are Runtime Capabilities or Integrations. Their dependency is
inward:

```text
Integrations → Capabilities → Runtime Harness → Agent Core
```

Workflow is not Agent Core. It may consume the Runtime/Core contracts, but Core
must not import workflow. The same rule applies to MCP, definition persistence,
voice, concrete guardrails, and concrete long-term memory providers.

## Dependency direction

Core must not import backend, application, frontend, evaluation,
observability, cost-analysis, retrieval implementations, SQLAlchemy,
`agentlabkit_db`, or concrete Runtime capabilities. In particular, the loop
must reach tools through `ToolExecutionCallback`/protocols rather than through
MCP, HTTP, Knowledge, Workflow, or database tool adapters.

The whole `agent_runtime` package may still contain integrations such as the
DB-backed definition loader. That is an adapter concern and is deliberately
not a package split in this iteration.

## Runtime facts and Core events

Runtime owns execution facts and identity (`run_id`, `trace_id`, spans, and
lifecycle facts). Core-internal algorithm events are a separate conceptual
layer. Runtime maps Core activity to `RuntimeEvent`; Trace, Cost, and
Evaluation consume those Runtime facts.

The existing semantic mapping and span machinery are a protected seam and a
future extraction candidate. New loop algorithms must not be rejected merely
because they do not fit today's RuntimeEvent taxonomy. The semantic layer must
adapt to Core, not constrain future Core algorithms.

## Public API stability

Top-level exports do not all carry the same compatibility promise:

- **Stable Runtime API:** `AgentRuntime`, `AgentTurnRequest`,
  `AgentTurnResult`, `AgentRun`, and execution-facing contracts.
- **Experimental / Capability API:** `WorkflowEngine`, `McpClientManager`,
  `SkillRegistry`, and multi-agent helpers.
- **Internal API:** `run_agent_loop`, loop internals, semantic mapping helpers,
  and internal span machinery.

Adding a top-level export must not be treated as an automatic permanent API
commitment.

## Future split triggers

Consider a Workflow package split only when durable execution, workflow
version/lifecycle, distributed scheduling, complex checkpoint/recovery, a
large workflow-only dependency set, or frequent Core changes caused by
Workflow provide concrete evidence.

Consider an `agent_core` split only when independent publication or embedding,
high-frequency independent loop experiments, capability dependencies that
block Core, or materially larger DB/MCP/Workflow installs and tests justify
it. No split is planned now.

Pi is an R&D reference, not an upstream source-synchronization target. Ideas
may be read, evaluated against AgentLabKit Core, and implemented independently
while preserving the Execution Model boundary.

## Review questions

For substantial Runtime, Workflow, memory, MCP, multi-agent, or semantic-event
changes, review whether the change modifies Core or only the Harness/Capability;
adds concrete platform knowledge to the loop; adds a Core dependency; lets the
RuntimeEvent taxonomy constrain the algorithm; could use a protocol/hook/
callback; preserves Workflow→Core direction; enlarges the stable API; and keeps
Application, Evaluation, Observability, and Frontend mostly untouched if the
loop is replaced.

