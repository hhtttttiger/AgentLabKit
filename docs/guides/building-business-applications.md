# 使用 AgentLabKit 构建业务应用

这是一份平台使用指南，不是 AgentLabKit 的内部架构规范。它说明业务产品如何使用 AgentLabKit 的公开平台能力，并明确记录当前 `main` 已验证的支持范围与缺口。

> 验证基线：`main`，commit `214010a`。公开 surface 的结论以当前 FastAPI routes、schemas 和 application contracts 为准；未来能力不能按本指南提前假设为已支持。

## 1. 核心边界

AgentLabKit 提供 Agent 执行、LLM、Tools/MCP、Knowledge/RAG、Memory、Guardrails、Workflow、Run/Trace、Cost、Dataset、Evaluation、Compare 和 Replay 等通用 AI execution 能力，但不是 CRM、客服、法务、教育或销售领域框架。

```text
Business Application
        │ business context
        ▼
Business Backend / AgentLabKit adapter
        │ public Platform API
        ▼
AgentLabKit AI execution
```

业务应用拥有客户、订单、合同、工单、权限和业务状态等业务事实；AgentLabKit 拥有 Agent、Run、Trace、Tool、Retrieval、Evaluation 等 AI execution facts。不要为了执行 Agent 把 `customer_id`、`order_id` 或 `contract_id` 变成 Runtime identity。

## 2. 推荐集成方式

```text
Business UI
    ↓
Business Backend
    ├── authentication / authorization
    ├── business data and domain rules
    ├── business API / tool adapter
    └── AgentLabKit Platform API
            ├── Agent definition and version
            ├── Knowledge / RAG
            ├── Agent invocation
            └── Run / Trace / Dataset / Evaluation
```

业务应用不应依赖 Agent Loop、`RuntimeEvent`、projector、private store 或 evaluator internals。AgentLabKit Admin 是工程控制台，不是业务产品 UI；业务产品可以拥有独立的 Web、Mobile 或 Desktop 前端。

当前 `main` 已验证的 HTTP 路径包括：

| 业务需求 | 当前 public surface | 结论 |
| --- | --- | --- |
| 管理 Agent 与版本 | `/api/agents`、`/api/agents/{agent_key}/versions` | 可用 |
| 绑定 Tools / Knowledge | version binding routes | 可用；Knowledge 是 version 级 binding |
| 调用 Agent | `POST /api/ai/invoke/agents/{agent_key}/turn` 及 `/stream` | 可用；支持 message、session、user、history |
| 管理和检索 Knowledge | `/api/knowledge-bases` 及 `/{kb_id}/search` | 可用；授权 scope 仍需业务侧补齐 |
| 读取 Run | `GET /api/runs/{run_id}` | 可用；按认证用户做 ownership check |
| Replay / Capture | `POST /api/runs/{run_id}/replay`、`/capture` | 可用 |
| 查看 Trace / Cost / Evaluation | `/api/traces`、`/api/cost`、`/api/eval` | 已有工程 surface，按各自 contract 使用 |

## 3. Business Context

业务侧可以传递本次执行真正需要的上下文，例如 `user_id`、`tenant_id`、`resource_id`、locale、权限结果或业务 metadata；不要复制完整业务对象模型。

当前限制必须明确：Agent turn 的 HTTP request 只有 `Message`、`SessionId`、`UserId` 和 `History`，没有 `metadata`、`tenant_id`、`resource_id` 或显式 permission scope。底层 `ExecuteAgentCommand` 和 Runtime `ExecutionContext` 已有 metadata contract，但现有 HTTP adapter 没有把这些字段公开出来。因此需要业务上下文时，应由 Business Backend 保存关联并在业务 Tool/API 层执行授权；不要把“底层 contract 存在”误写成“HTTP 集成已支持”。

## 4. Knowledge、Tool 与权限

Knowledge 适合产品文档、FAQ、制度、SOP、合同文本和培训资料等相对稳定的非结构化信息。实时订单状态、余额、库存、权限和具有副作用的操作应通过 Tool/MCP 调用 Business API。

```text
Agent → Tool → Business API → authorization / transaction / domain rules
Agent → Knowledge → documents / chunks
```

业务权限必须由 Business Backend 或业务 API authoritative 地判断。Prompt、Guardrail 和 LLM 不能替代权限系统，也不应让 Agent 直接访问业务数据库。

### Knowledge scope 的当前状态

Agent version 可以绑定一个或多个 Knowledge Base，Runtime 的 knowledge tool 会按这些 binding 搜索。这是“配置 scope”，不是多租户或用户级授权 scope。当前 `BackendKnowledgeProvider` 的实现按绑定的 knowledge-base ids 检索，代码注释仍将权限过滤列为后续工作；现有 HTTP contract 也没有传入业务侧的 allowed scope。

因此，涉及敏感文档的业务应用必须先在自己的授权层解析出允许的资源，再通过受控的业务 API/Tool 提供给 Agent。当前平台不应被描述为已经提供 tenant-aware、user-aware 的 Knowledge authorization。

## 5. Agent、Run 与业务关联

业务调用 Agent 后，应把返回的 `run_id` 作为业务侧关联值保存：

```text
SupportTicket #8921 ── stores ── run_id
```

`run_id` 是一次真实 AI execution 的 identity；`trace_id` 是观察该 Run 的 projection 关联，不可互换。`DatasetExample.example_id` 也不是 `run_id`。

当前 Run API 支持按 `run_id` 读取、Replay 和 Capture，并且对已认证用户执行 ownership check。当前没有 `business_resource_id`、通用 association resource，或“按业务实体查询 Runs”的 public API。因此“业务系统保存 `run_id` 并链接到自己的记录”是已支持的集成方式；“让 AgentLabKit 管理业务实体关联”仍是 gap。

## 6. 工程闭环

```text
Define Agent
    ↓
Connect Knowledge / Tools
    ↓
Run → Inspect Run / Retrieval / Cost
    ↓
Capture important production cases
    ↓
Dataset → Evaluate → Compare
    ↓
Improve and release
```

质量、成本、延迟和可靠性应一起观察。回答错误时，先从对应 Run 判断是 Retrieval、Knowledge、Tool、Prompt、Model 还是 Guardrail 问题，再决定修改位置；不要只修改 Prompt。

## 7. 新需求放在哪里

- 订单、客户、合同、审批和业务权限：Business Application。
- Tool execution、Retrieval、Guardrail、Run、Evaluation：AgentLabKit。
- 实时业务事实或有副作用的业务操作：Business API + Tool。
- 供模型参考的非结构化资料：Knowledge。
- Agent 开发、调试、评估和 Replay：AgentLabKit Engineering Surface。

详见配套的 [Business Integration Readiness Audit](business-integration-readiness-audit.md)。
