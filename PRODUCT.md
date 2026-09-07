# Product

## Register

product

## Persona

### Agent Engineer

开发者使用 AgentLabKit 构建 Agent、组合 Model / Capabilities / Knowledge、运行真实请求、检查执行行为，并通过 Dataset / Evaluation / Compare 持续证明改进。

## Product Purpose

AgentLabKit 为 Agent Engineer 提供从构建到交付的工程闭环：让复杂的 Agent 工程流程清晰可操作，优先使用真实执行和可复用资产，并支持持续演进 Agent。

## Core Journey

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

Published Agent 是 executable target；Draft 是可编辑的 next version。生命周期规则：Draft-only 不提供 Test；Published-only 测试 Published；Published+Draft 仍测试 Published。

## Improve Journey

```text
Run
→ Add to Dataset
→ Evaluate Dataset
→ Inspect failures
→ Modify Agent
→ Re-evaluate
→ Compare Baseline / Candidate
```

产品语言使用 Add to Dataset、Evaluate Dataset、New Evaluation、Evaluation Run、Run Again、Compare、Baseline 和 Candidate。Capture、DatasetExample、RunConfig、Target Type / Target Key 是实现或 domain concepts，不是 primary UI wording。

## Knowledge / RAG Journey

```text
Prepare Knowledge
→ Test Retrieval
→ Use in Agent
→ Test Agent
→ Inspect Retrieval
→ Diagnose
```

“Use Knowledge”是产品语义：产品应让用户表达“让这个 Agent 使用这份 Knowledge”，而不是要求用户理解底层多个 binding mechanism。它由 selected Knowledge binding 与 usable `knowledge_search` 共同组成，但不改变两个 domain facts 的边界。

## Retrieval Diagnosis

产品必须区分：

```text
No Retrieval ≠ Zero Results ≠ Retrieval Failure
```

用户应能看到 retrieval 是否发生、query、attempts、result count、bounded evidence previews、failure 和 retry，并据此获得 facts + guidance，而不是 automatic root-cause classifier：expected evidence missing 时调查 Retrieval；expected evidence present 时调查 Agent response / instructions。

## Product Language

- **Run** — 一次真实执行。
- **Trace** — 对这次执行的观测。
- **Dataset** — 可复用测试资产。
- **Evaluation Run** — 一次 Dataset evaluation。
- **Baseline** — 比较基线。
- **Candidate** — 待验证版本。
- **Knowledge** — Agent 可使用的资料。
- **Retrieval** — 一次实际检索行为。

## Product Principles

- 真实执行优先于演示数据。
- Historical execution truth must remain historical；Trace evidence preview 不是当前 Knowledge state。
- Run != Trace；不得把 Trace 冒充 Run。
- 从 Run 到 Inspect、Replay、Add to Dataset、Evaluate、Compare 的路径必须连续。
- 复用已有 public contract、资源查询和设计系统，不制造平行入口。
- 语义事实优先于视觉推断，尤其是 identity、ownership、status 和 verdict。
- 每个功能都应为下一次 Agent 改进留下可用资产。

## Brand Personality

易用、可复用、可进化。产品应让复杂的 Agent 工程流程清晰可操作。

## Anti-references

避免为了展示模块完整性而堆叠页面、占位数据或重复抽象。避免用分数猜测 verdict，或为了短期 UI 需求破坏稳定的 ownership 和 application contract。

## Accessibility & Inclusion

保持基本可用性，包括清晰的状态文本、可理解的错误和空状态，以及标准 HTML 交互元素。
