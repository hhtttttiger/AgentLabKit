# Desktop Product Projection

AgentLabKit is a complete Agent Engineering capability platform. AgentLab
Desktop is a product projection of those capabilities for personal,
local-first, daily Agent Engineering work.

Desktop is not a local copy of the Server administration console. It is not a
page-for-page mapping of the AgentLabKit module catalog.

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

For example, a Desktop execution flow may eventually project model capability
as:

```text
New Session
  Agent  Native
  Model  <model selector>
```

This is a projection example, not a claim that the current Desktop already has
a Model Settings surface. Server may separately expose a complete Model
Management area for providers, credentials, endpoints, capabilities, pricing,
and policies.

## Desktop and Server

Desktop and Server may consume the same Platform Capability while presenting
different products:

| | Desktop | Server |
|---|---|---|
| Primary user | Individual developer | Teams and platform operators |
| Workflow | Local-first daily Agent work | Shared platform and governance |
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
