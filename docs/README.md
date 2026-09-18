# 文档导航与状态约定

这份仓库同时经历过通用 Agent 库、平台服务、回放/评估和桌面端几个阶段。文档按下面的状态阅读：

- **Current**：描述当前 source truth，可作为开发和集成依据。
- **Historical**：记录某次设计、迁移或审计结果；其中的分支名、commit、migration 编号和“待办”不代表当前状态。
- **Deprecated**：描述已经退出产品入口的实现，仅用于迁移或考古。

## 当前权威入口

- 产品定位：[`PRODUCT.md`](../PRODUCT.md)
- Application use cases：[`packages/application/README.md`](../packages/application/README.md)
- Runtime 与 identity：[`architecture/execution-model-v2.md`](architecture/execution-model-v2.md)
- FastAPI adapter boundary：[`architecture/fastapi-adapter-boundary.md`](architecture/fastapi-adapter-boundary.md)
- Streaming contract：[`architecture/agent-turn-streaming.md`](architecture/agent-turn-streaming.md)
- Desktop Product Projection：[`architecture/desktop-product-projection.md`](architecture/desktop-product-projection.md)
- Desktop runtime modes：[`desktop-modes.md`](desktop-modes.md)
- Docker 调试：[`operations/docker-debug.md`](operations/docker-debug.md)
- 业务应用集成：[`guides/building-business-applications.md`](guides/building-business-applications.md)
- Library-first Agent 开发：[`guides/building-agents-with-packages.md`](guides/building-agents-with-packages.md)

当本文档与 source、package `README.md` 或仓库级 `AGENTS.md` 冲突时，以 source 和这些边界说明为准。

## 历史材料

`docs/plans/`、[`architecture-hardening-progress.md`](architecture-hardening-progress.md)、[`plans/observability-v2-migration.md`](plans/observability-v2-migration.md) 和 [`desktop-app-plan.md`](desktop-app-plan.md) 主要保留演进记录。它们已经加上历史标记，但不应作为新功能的实施清单。

新增公共 route、Application use case、Runtime identity 或桌面模式时，先更新对应的当前权威文档，再把过时的计划改成 Historical 或 Deprecated。
