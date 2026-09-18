# Desktop Product Projection

AgentLabKit is an Enterprise Agent Engineering Platform. AgentLab Desktop is
the local-first Agent Developer Workbench: a product projection of those
capabilities for developing, running, inspecting, and improving enterprise
Agents in a local project.

Desktop is not a local copy of the Server administration console. It is not a
page-for-page mapping of the AgentLabKit module catalog, and it is not a
universal Agent launcher or replacement client for external Agents.

AgentLab Server is the shared Enterprise Agent Engineering Platform for team
and enterprise environments. Desktop and Server may consume the same platform
capabilities while presenting different products.

> **Module != Product Page**

This document is the long-term authority for Desktop product composition. It
does not define frontend routes, API contracts, or Runtime semantics.

## Product categories

Desktop design starts from three categories:

### Work Objects

Engineering assets that a user creates, inspects, operates, or reuses:

- Session
- Run
- Case
- Dataset
- Evaluation
- Replay
- Compare

These may become first-class Desktop surfaces when they support a real
engineering journey.

### Work Actions

Actions a user performs to complete an Agent Engineering loop:

- Run
- Inspect
- Save as Case
- Replay
- Evaluate
- Compare

Desktop journeys should make these actions discoverable in the context of the
relevant Work Objects.

The central Desktop path is:

```text
Agent Developer
      ↓
   Project
      ↓
   Session
      ↓
Enterprise Agent → Runtime → Run
      ↓
Inspect / Capture → Dataset → Evaluation → Compare → Improve
```

Native Agent means the AgentLabKit Reference / Enterprise Agent Runtime. Its
value comes from the enterprise instructions, models, knowledge, tools,
memory, guardrails, and workflows that are composed into it.

### Platform Capabilities

Underlying capabilities that support Work Objects and Work Actions:

- Models and Providers
- Tools
- Guardrails
- Retrieval
- Memory
- Observability
- Cost Analysis

The existence of a Platform Capability or backend Module does not by itself
justify a Desktop first-level page or navigation item.

## Capability projection

Platform Capabilities should normally be absorbed into a concrete work context
instead of being copied as management modules:

| Platform Capability | Typical Desktop projection |
|---|---|
| Models / Providers | Settings, execution configuration, model selector |
| Observability | Run Inspector, timeline, trace and execution details |
| Cost Analysis | Run, Evaluation, Compare evidence |
| Tools | Agent capability, settings, execution configuration |
| Guardrails | Advanced execution configuration or Settings |
| Memory | Agent working context where appropriate |
| Retrieval | Knowledge context or Run Inspector |
| Evaluation | Core engineering action and, where justified, a first-class surface |

Desktop can consume the full platform capability set without exposing the full
platform management interface.

For example, Desktop may project capabilities into the Agent Developer journey
as follows. These are non-binding examples, not a claim that every surface is
already implemented:

| Platform capability | Desktop projection |
|---|---|
| Model Gateway / Providers / Models | Settings → Models; Agent Configuration → Model |
| Retrieval / Vector Store / Knowledge APIs | Agent → Knowledge |
| Tool Runtime / Tool Registry | Agent → Tools |
| Trace / Events / Metrics | Run Inspector |
| Cost Analysis | Run / Evaluation / Compare |

An execution flow may eventually project model capability as:

```text
New Session
  Agent  Native / Enterprise Agent Runtime
  Model  <model selector>
```

External Agents are a separate integration boundary. Capture / Import and
Replay / Evaluation may consume external execution components when an
integration preserves the relevant Run facts and provenance. Interactive
hosting of an external Agent's conversation, resume, tool approval, session
state, streaming, permissions, sandbox, or provider-specific configuration is
not the current Desktop product goal.

The interactive New Session selector must list only executors that really
implement the Native Agent streaming contract. External Agent integrations
belong in Replay, Evaluation, or capture/import surfaces; an external option
must never be routed into Native streaming by convenience.

Codex is currently retained as an External Agent integration for Replay and
Evaluation where supported. Cross-Agent Replay remains valuable because it
checks whether Cases, Datasets, Runs, Evaluation, and Compare assets survive a
change in execution component. Replay also remains a primary Native Agent
improvement loop for model, prompt, tool, knowledge, retrieval, runtime, and
guardrail changes.

Server may separately expose a complete Model Management area for providers,
credentials, endpoints, capabilities, pricing, and policies.

## Desktop and Server

Desktop and Server may consume the same Platform Capability while presenting
different products:

| | Desktop | Server |
|---|---|---|
| Primary user | Agent Developer | Teams and platform operators |
| Workflow | Local-first enterprise Agent work | Shared enterprise Agent Engineering |
| Organization | Work Objects and Work Actions | Resources, capabilities, and operations |
| Configuration | Contextual and minimal | Shared, governed, and operational |

The distinction is a product projection boundary, not a claim that the two
products need different execution facts or incompatible domain contracts.

## Desktop surface rule

Before adding a Desktop surface, answer:

> Is this a Work Object, a Work Action, or a Platform Capability?

Work Objects and Work Actions may enter the primary journey when a real user
journey requires them. Platform Capabilities should default to projection into
Settings, Execution Configuration, Run Inspector, Case / Dataset,
Evaluation / Compare, or another concrete engineering context.

If the answer to “Why would a user open this during a daily Agent Engineering
journey?” is unclear, the capability should not become a first-level Desktop
surface.

## Execution semantics remain unchanged

Product projection categories do not change execution ownership:

```text
Session  = Desktop UX / product concept
Run      = execution fact
Trace    = observation of execution facts
```

Session is not Run. Runtime remains the owner of execution identity and facts;
Trace remains an observability projection. See [Execution Model v2](execution-model-v2.md).
