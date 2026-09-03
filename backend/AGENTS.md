# Backend

## 职责

`backend` 是 FastAPI transport 与 composition layer。它暴露 public HTTP/SSE contract，连接 package capabilities，拥有 module resource services，并运行 indexing worker。它不是平台 orchestration layer。

## Endpoint ownership

- **Platform action → Application Use Case**：agent turn/replay/capture，以及 agent-target evaluation/compare。
- **Resource API → Module Service**：authentication、agents、model catalog、knowledge bases、chat、files、glossary、memories、datasets、budgets 和 definitions。
- **Projection/query → Reader、Store 或 aggregator**：Runs、traces、costs、model usage 和 evaluation-run reads。

使用 [`docs/architecture/fastapi-adapter-boundary.md`](../docs/architecture/fastapi-adapter-boundary.md) 中的现有边界。`runs` module 是 Run reads、replay 和 capture 的 HTTP adapter；它不拥有 Runtime identity。

## 规则

- 保持 routes 简单：验证 HTTP input、认证/授权、映射 DTO、委托调用，并将结果适配为 HTTP 或 SSE。
- 不要在 routes/services 中构造 `AgentRun`、生成 execution IDs、计算 evaluation verdicts，或根据 Run data 重建 Trace。
- 将 application orchestration 保持在 `packages/application`；将 CRUD/resource behavior 保持在所属 module service。
- 保留 public envelope 和 SSE contract；内部 `RuntimeEvent` values 不会自动成为 public API。
- Web indexing 只入队。`src/worker.py` 在独立进程中消费队列。

## 关键路径

- `src/main.py` — app factory、lifespan、composition root、router registration。
- `src/runtime/` — package adapters 和 application wiring。
- `src/modules/` — HTTP modules 和 resource services。
- `src/modules/runs/` — Run reader 和 Application Use Case adapters。
- `alembic/` — database migrations。

## 验证

从 `backend/` 运行变更模块的 targeted tests。对于 runtime/application boundary 变更，同时运行 `packages/*/tests` 下的相关 package tests。调用 backend modules 时，使用 `PYTHONPATH=src` 验证 imports。

## 参考

- [根目录 instructions](../AGENTS.md)
- [FastAPI adapter boundary](../docs/architecture/fastapi-adapter-boundary.md)
- [Execution Model v2](../docs/architecture/execution-model-v2.md)
