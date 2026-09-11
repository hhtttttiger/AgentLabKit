# Business Integration Readiness Audit

## Audit scope

- 基线：`main`，commit `214010a`（2026-09-11）。
- 检查对象：业务应用只依赖 Platform API / Application boundary 的典型路径。
- 证据：[`backend/src/main.py`](../../backend/src/main.py) 的 router mounting、各模块 router/schema、[`packages/application`](../../packages/application) contracts，以及 Runtime/Knowledge adapter。Run identity 的既有边界也见 [`docs/public-execution-api.md`](../public-execution-api.md)。

## Executive result

AgentLabKit 当前已经具备一条可用于内部或受控业务后端的最小集成路径：创建/发布 Agent → 配置 Tool 与 Knowledge binding → 调用 Agent → 取得 `run_id` → 读取、Replay 或 Capture Run。

这条路径还不能被描述为完整的 multi-tenant business integration contract。最重要的未完成项是：业务上下文没有在 Agent turn HTTP contract 中公开传递；Knowledge scope 没有 tenant/user/permission enforcement；平台没有 first-class business-resource association API。

## Findings

| Area | Evidence on `main` | Status | Integration implication |
| --- | --- | --- | --- |
| Agent invocation | [`ai_invoke/router.py`](../../backend/src/modules/ai_invoke/router.py): `POST /api/ai/invoke/agents/{agent_key}/turn` and `/stream`; `AgentTurnRequest` has message/session/user/history | Supported | Business Backend can invoke a published Agent and receive Run identity |
| Agent configuration | `/api/agents`, version routes, tool bindings, knowledge-base bindings | Supported | Agent configuration can remain behind public resource APIs |
| Knowledge retrieval | `/api/knowledge-bases/{kb_id}/search`; Runtime calls `search_bound_knowledge_bases` | Partially supported | Version bindings constrain search, but do not prove caller authorization |
| Knowledge authorization | [`knowledge_provider.py`](../../backend/src/modules/knowledge_base/knowledge_provider.py) searches bound ids; its comment says permission filtering is future work; no tenant/allowed-scope input in turn request | Gap | Sensitive Knowledge needs Business Backend authorization before invocation/tool exposure |
| Business context | `ExecuteAgentCommand.metadata` and Runtime `ExecutionContext.metadata` exist, but `AgentTurnRequest` does not expose metadata/resource/tenant/scope | Gap | Do not document these fields as currently available through Platform HTTP API |
| Run identity | [`contracts/run.py`](../../packages/agent_runtime/src/agent_runtime/contracts/run.py) keeps Runtime ownership of `run_id`/`trace_id`; invocation returns both; `Run != Trace` remains the contract | Supported | Store `run_id` in the business system; never substitute `trace_id` |
| Run ownership | `/api/runs/{run_id}` uses `ensure_run_access`; list is scoped to authenticated user | Supported with limitation | User ownership exists; tenant/resource ownership is not a platform contract |
| Run association | Capture/replay operate on Run IDs; no business-resource association route or query | Gap | Business DB must own `business_entity ↔ run_id` mapping |
| Tools / business operations | Agent tool definitions and bindings are public resources; business authorization remains outside AgentLabKit | Supported as adapter pattern | Expose business capabilities through an authorized Business API, not direct DB access |
| Engineering loop | Run read, Trace, Cost, Dataset/Evaluation routes are mounted | Supported | The inspect → capture → evaluate loop is available, subject to module contracts |

## Recommended supported path today

```text
Business Backend
  1. authenticate and authorize the caller
  2. resolve allowed business and Knowledge scope
  3. call Agent invocation API
  4. save returned run_id beside the business record
  5. use Run/Trace APIs for inspection
  6. capture failures and evaluate revisions
```

For Knowledge-sensitive flows, the Business Backend must prevent an unauthorized Knowledge Base or business Tool from being reachable. A static Agent version binding alone is not sufficient evidence of end-user authorization.

## Gaps to close before claiming a general public integration contract

1. Define a public Agent invocation context contract for tenant, resource, locale, permission scope, and metadata, including retention and redaction rules.
2. Add an authoritative Knowledge authorization boundary that receives the caller's allowed scope and enforces it before content reaches the model.
3. Decide whether business association belongs entirely to the Business Backend or whether AgentLabKit should expose a generic association/query contract. If the latter, specify ownership, authorization, and whether associations are execution facts or business projections.
4. Add contract tests proving that invocation, retrieval, Run reads, and Tool calls preserve the same caller/tenant authorization boundary.

Until these are implemented and tested, the guide should say “supported for a controlled Business Backend adapter” rather than “ready for arbitrary multi-tenant business applications.”
