# Future Product Ideas

本文档记录尚未承诺、尚未进入当前 roadmap 的产品假设。这里的内容用于保留产品方向和讨论背景，不构成实现计划、Domain Contract、数据模型或 schema。

## Evidence-backed Skills

**Status:** Future Product Hypothesis · Not committed · Not implemented

### 核心假设

AgentLab 未来可能将真实 Agent 工作中、经过 Replay / Evaluation 验证的工程经验，沉淀为可复用、可追溯、可验证的 Skill。

这里的 Skill 未来可能不只是人工编写的一段 Instructions，而是从真实 Agent Engineering Experience 中逐渐沉淀出的可执行工程知识。

潜在生命周期：

```text
Enterprise Work
     ↓
    Run
     ↓
   Case
     ↓
 Dataset
     ↓
Replay / Evaluation
     ↓
Validated Experience
     ↓
   Skill?
     ↓
Enterprise Agent
     ↓
   New Run
     ↓
 New Evidence
```

这只是产品假设。它不表示当前已经存在对应的数据模型，也不改变现有 Execution Model。

### 初步资产语义

以下定义用于帮助讨论未来方向，不是正式的领域契约：

| 资产 | 初步理解 |
| --- | --- |
| **Run** | 实际发生了什么。Run 是 execution fact；现有 Execution Model 的定义保持不变。 |
| **Case** | 一个有价值的具体经验：这个具体问题以前是如何被处理的。 |
| **Dataset** | 可复用 Case 的集合或 evidence set，可作为组织和验证多条经验的基础。 |
| **Replay** | 让过去的经验再次可执行，用于观察相同经验是否仍可执行，以及更换 Agent、Model 或 Config 后的结果。 |
| **Evaluation** | 判断一条经验是否仍然有效，为经验提供 evidence，而不只是保存历史。 |
| **Skill** | 未来可能表示可应用于未来工作的、经过验证的可复用工程知识。 |

一个帮助理解的非正式对比是：

```text
Case  = “以前这个具体问题是怎么解决的”
Skill = “以后遇到这一类问题，可以怎么解决”
```

### 潜在产品闭环

```text
                 Work
                   │
                   ▼
                  Run
                   │
                   ▼
                 Case
                   │
                   ▼
                Dataset
                   │
            Replay / Evaluate
                   │
                   ▼
                 Skill
                   │
                 apply
                   ▼
              Future Work
                   │
                   ▼
                New Run
                   │
                   └────→ New Evidence
```

该闭环的核心描述是：

> Replay makes past experience executable again.
>
> Evaluation determines whether that experience remains effective.
>
> Skill brings validated experience into future work.

### 与 instruction-only Skill 的潜在差异

这里不贬低或重新定义行业中已有的 Skill。仅记录 AgentLab 未来可能探索的差异化方向：

```text
普通 Skill：
Instructions
     ↓
Execution

AgentLab 未来可能探索：
Evidence
     ↓
Validated Knowledge
     ↓
Skill
     ↓
Execution
     ↓
New Evidence
```

因此，未来的 AgentLab Skill 可能不仅包含 Instructions，还可能关联：

```text
Skill
├── Instructions
├── Applicability
├── Resources
├── Evidence
│   ├── Cases
│   ├── Datasets
│   └── Evaluation Runs
└── Version History
```

上面的结构只表达可能的语义组成，不能当作已确定的 schema。应继续使用 `may`、`could` 和 `potential` 来描述它。

### Cross-Agent 的潜在意义

AgentLab 已经支持在适用的边界内让不同的 Agent executor 消费工程资产。
Cross-Agent Replay 仍是当前有效的 engineering interoperability 能力；未来
Evidence-backed Skills 可能与它形成关系：

- 同一个 Case 可以在不同 Agent executor、Model 或 Config 上 Replay；
- Evaluation 可以帮助判断一条经验是特定于某个 Agent，还是能够跨 executor 迁移；
- 经过多个执行环境验证的经验，未来可能更适合作为可复用 Skill；
- 新的 Agent executor 也可能通过应用已有 Skill 产生新的 Run 和 evidence。

这仍然只是潜在方向，不意味着 Skill 必须跨 Agent，也不意味着当前 Replay /
Evaluation contract 需要改变。它同样不意味着 AgentLab 需要托管每个外部
Agent 的 interactive session UX。

### 当前边界与非目标

- 本文档不新增 Skill domain、API、数据库表、schema、Application use case 或 Runtime fact。
- 不把 `Case`、`Skill` 或任何未来资产定义为当前正式 contract。
- 不改变 `Run`、`Trace`、`DatasetExample.example_id`、Replay 或 Evaluation 的现有 ownership 和 identity 规则。
- 当前 roadmap 不包含 Skills 实现；未来若进入设计阶段，应另行提出具体问题、契约和验证标准。
