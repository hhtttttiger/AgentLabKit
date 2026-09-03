# AgentLabKit

## 适用范围

仓库级 instructions。更近的 `AGENTS.md` 可以为其子树增加约束，但不得与本规则冲突。

## 架构不变量

- Runtime 拥有 execution facts 与 identity（`run_id`、`trace_id`、spans、lifecycle events）。
- `Run != Trace`：Trace 是真实 Run 的 Observability projection。
- Projectors、Replay、Evaluation、HTTP adapters 和 Frontend 不得创建 execution facts 或 IDs。
- `run_id` 永远不是稳定的 DatasetExample `example_id`。
- Application Use Case v1 已封版：`ExecuteAgent`、`ReplayRun`、`CaptureRunAsDatasetExample`、`EvaluateDataset` 和 `CompareEvaluationRuns`。
- FastAPI 是 adapter，不是平台业务层。Platform actions 委托给 Application Use Cases；resource APIs 使用 Module Services；读取使用 Readers/Stores/Projections。
- `llm_gateway` 是唯一的 LLM API entrypoint。`retrieval` 是唯一的 document/embedding/vector-retrieval engine。
- Backend web indexing 只入队；`backend/src/worker.py` 消费队列。

这些边界是稳定的。只有出于具体的正确性或产品需求才可修改，并同步更新权威架构说明。

## 仓库结构

- `packages/application` — framework-neutral platform use cases。
- `packages/agent_runtime` — Runtime、events、tools、guardrails、memory 和 workflows。
- `packages/llm_gateway` / `packages/retrieval` — 基础 LLM 与 RAG 能力。
- `packages/evaluation`、`packages/observability`、`packages/cost_analysis`、`packages/memory` — 平台 projections 和 services。
- `packages/db` / `packages/infra` — 共享数据库与基础设施 primitives。
- `backend` — FastAPI transport、composition root、module services 和 worker。
- `frontend/admin` — public HTTP/SSE contract 的 React client。
- `desktop` — standalone PySide6 client。
- `docs/architecture` — 长篇架构决策。

## 修改规则

- 保持 routes 简单并使用现有 ownership boundary；不要新增通用的 Controller、Facade、Manager 或 command-bus 层。
- 不要为了保留过时文档而修改已封版的 contracts。更新文档以匹配 source truth。
- 将 provider-specific integrations 保持在 package protocols/adapters 后面。
- 保留明确的 identity 和 ownership fields；不要从排序、名称或 fallback IDs 推断。

## 验证

使用最近的 package guidance 执行 targeted tests。仅修改文档时，验证 links 和 paths，搜索过时的架构术语，并确认文档中的每个 command/script 都存在。Frontend contract 变更需在 `frontend/admin` 运行 `npm run check`、`npm run test` 和 `npm run build`。

## 参考

- [Execution Model v2](docs/architecture/execution-model-v2.md)
- [FastAPI adapter boundary](docs/architecture/fastapi-adapter-boundary.md)
- [Streaming contract](docs/architecture/agent-turn-streaming.md)
