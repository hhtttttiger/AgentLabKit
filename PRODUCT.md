# Product

## Register

**AgentLabKit — Enterprise Agent Engineering Platform**

AgentLabKit helps enterprises build, run, observe, evaluate, and continuously
improve Agents that combine their own instructions, models, private knowledge,
internal tools, memory, guardrails, workflows, and evaluation criteria.

Its product loop is:

```text
Build
  ↓
Run
  ↓
Observe
  ↓
Capture Evidence
  ↓
Evaluate
  ↓
Improve
  ↓
Repeat
```

AgentLabKit is not intended to be a stronger general-purpose Coding Agent or a
replacement for Codex, Claude Code, or another consumer or frontier Agent. Its
long-term value is the engineering lifecycle around an enterprise's own
Agents.

## Product surfaces

### AgentLab Desktop

AgentLab Desktop is a **local-first Agent Developer Workbench**. It helps an
Agent Developer work in a project, run an enterprise Agent, inspect execution,
capture useful evidence, and move that evidence into Case, Dataset,
Evaluation, Replay, and Compare workflows.

Desktop is not a universal Agent launcher, and it is not a Server
administration console.

### AgentLab Server

AgentLab Server is a **shared Enterprise Agent Engineering Platform** for team
and enterprise environments. Its natural future scope includes shared Agents,
Datasets, Evaluations, deployment/runtime infrastructure, governance,
observability, cost, production evidence, and collaboration. This describes a
product boundary, not a feature checklist for the current milestone.

## Native Agent

Native Agent means the AgentLabKit **Reference / Enterprise Agent Runtime**.
It is the runtime used to build and run an enterprise-custom Agent; it is not
AgentLab's competitor to Codex and is not expected to beat external frontier
Agents.

Conceptually:

```text
Enterprise Agent
    │
    ├── Instructions
    ├── Model
    ├── Knowledge
    ├── Tools
    ├── Memory
    ├── Guardrails
    └── Workflow
            │
            ▼
         Runtime
            │
            ▼
           Run
```

The Agent's value comes from the enterprise capability combination and its
engineering evidence, not from competing with a general-purpose Coding Agent.

## Product ownership boundary

AgentLab owns the Agent Engineering lifecycle and its long-lived engineering
assets. The core assets are:

- Run
- Case
- Dataset
- Evaluation
- Compare
- Replay
- Observability facts
- Cost facts

Agent implementation is an execution component, not the long-lived center of
AgentLab's product model. Implementations may change while these assets remain
useful for diagnosis, validation, and improvement. Evidence-backed Skills
remain a future product hypothesis; they are not implemented or committed
roadmap scope.

## External Agent boundary

AgentLabKit preserves External Agent integration where it creates useful
engineering interoperability. It does not aim to reproduce every External
Agent's native interaction experience.

The integration levels are:

### Level 1 — Capture / Import

```text
External Agent
      ↓
execution evidence
      ↓
     Run
```

The goal is to bring real external execution results into AgentLab engineering
assets where the integration can preserve authoritative facts and provenance.

### Level 2 — Replay / Evaluation

```text
Case / Dataset
      ↓
External Agent
      ↓
     Run
      ↓
 Evaluation
```

An External Agent can be an evaluation or replay executor when a stable
integration exists.

### Level 3 — Interactive Hosting

Continuous conversation, resume, tool approval, session state, streaming
semantics, and provider-specific UX belong to the External Agent's interactive
lifecycle. Level 3 is not an AgentLabKit core product goal today.

Accordingly, AgentLabKit does not promise a universal abstraction for
external chat, sessions, permissions, sandboxes, model configuration, context
management, or interactive lifecycle. New universal abstractions should only
be introduced for a concrete enterprise scenario with a stable contract.

## Codex integration

The current Codex integration remains an External Agent integration:

| Capability | Status |
|---|---|
| Replay | Supported where integrated |
| Evaluation | Supported where integrated |
| Run facts and external provenance | Preserved where available |
| Interactive Codex session hosting | Not a core supported capability |

Codex demonstrates that AgentLab engineering assets can be consumed by
different execution components. It does not turn AgentLab Desktop into a Codex
replacement client.

Cross-Agent Replay remains valid and important. It tests whether engineering
assets survive a change in execution component:

```text
Dataset
   │
   ├── Native Agent
   │
   └── External Agent
          │
          ▼
         Runs
          │
      Evaluation
          │
        Compare
```

Replay is also valuable without Cross-Agent execution. The primary improvement
path is:

```text
Real Work → Case → Dataset → Agent v1 → Evaluation
                                      ↓ improve
                              Agent v2 → Replay → Evaluation → Compare
```

Replay validates a changed Agent against past engineering evidence. Changes may
include models, prompts, tools, knowledge, retrieval, runtime, guardrails, or
future Skills.

## Core journeys

### Build and improve an enterprise Agent

```text
Create Agent
→ Configure
→ Publish
→ Test
→ Inspect Run
→ Diagnose
→ Add to Dataset
→ Evaluate
→ Modify Agent
→ Re-evaluate
→ Compare
```

Published Agent is the executable target; Draft is the editable next version.
Lifecycle rules: Draft-only does not provide Test; Published-only tests the
Published version; Published plus Draft still tests Published.

### Improve from evidence

```text
Run
→ Add to Dataset
→ Evaluate Dataset
→ Inspect failures
→ Modify Agent
→ Re-evaluate
→ Compare Baseline / Candidate
```

### Knowledge and Retrieval diagnosis

```text
Prepare Knowledge
→ Test Retrieval
→ Use in Agent
→ Test Agent
→ Inspect Retrieval
→ Diagnose
```

The product must distinguish:

```text
No Retrieval ≠ Zero Results ≠ Retrieval Failure
```

Users should be able to see whether Retrieval occurred, its query, attempts,
result count, bounded evidence previews, failures, and retries. The product
should provide facts and guidance rather than an automatic root-cause
classifier: missing expected evidence points toward investigating Retrieval;
present evidence points toward investigating the Agent response or
instructions.

“Use Knowledge” is the product language for asking an Agent to use a Knowledge
source. Users should not need to understand multiple underlying binding
mechanisms. The selected Knowledge binding and the usable `knowledge_search`
capability remain separate domain facts.

Product language uses **Add to Dataset**, **Evaluate Dataset**, **New
Evaluation**, **Evaluation Run**, **Run Again**, **Compare**, **Baseline**, and
**Candidate**. `Capture`, `DatasetExample`, `RunConfig`, `Target Type`, and
`Target Key` remain implementation or domain concepts rather than primary UI
wording.

## Platform capabilities and product projection

Models, Tools, Knowledge, Retrieval, Memory, Guardrails, Observability, Cost,
and Evaluation remain complete Platform Capabilities. They support the
Enterprise Agent Runtime and are not removed by the product focus.

`Module != Product Page`: a platform module does not automatically become a
first-level Desktop navigation item. Desktop should project capabilities into
the Agent Developer journey, such as model configuration in Settings,
Knowledge and Tools in Agent configuration, Observability in Run Inspector,
and Cost in Run, Evaluation, or Compare. These are projection examples, not a
claim that every surface is already implemented.

## Product language

- **Run** — one real execution; its identity and execution facts belong to the
  Runtime.
- **Trace** — an observability projection of a Run.
- **Case** — a captured piece of valuable work or evidence for engineering
  reuse.
- **Dataset** — a reusable collection of test cases.
- **Evaluation Run** — one process that evaluates an Agent against a Dataset.
- **Baseline / Candidate** — the two sides of a comparison.
- **Knowledge** — material an Agent may use.
- **Retrieval** — a retrieval behavior that actually occurred.

Run is not Trace, and Run identity is not a Dataset example identity.

## Product principles

- Real execution is preferred to demo data.
- Historical execution truth remains historical.
- Engineering assets should remain useful across Agent implementation changes.
- External integration should preserve facts and provenance instead of guessing
  provider-specific state.
- Existing public contracts, resource queries, and design-system patterns are
  preferred over parallel entrances and universal abstractions.
- Every feature should leave a useful asset for the next Agent improvement.

## Anti-references

Avoid building a general-purpose Agent client, reproducing every provider's
interactive UX, stacking first-level pages merely to display module
completeness, or introducing placeholder data and parallel abstractions.
Avoid guessing verdicts from scores, or changing Runtime, Replay, Evaluation,
Dataset, or Server contracts just to support this product-direction
realignment.

## Brand personality

The product should be clear, reusable, and evolvable. Complex Agent
Engineering work should be understandable and actionable without hiding the
facts that support an engineering decision.

## Accessibility and inclusion

Keep basic interactions usable: clear state text, understandable errors and
empty states, and standard HTML controls.
