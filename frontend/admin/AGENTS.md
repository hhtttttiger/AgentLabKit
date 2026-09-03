# Admin frontend

## 职责

`frontend/admin` 是 public FastAPI HTTP/SSE contract 的 React 19 + TypeScript client。它拥有 presentation、client state、routing 和 API-to-view-model mapping；不拥有 backend execution semantics。

## Contract rules

- 将 HTTP calls 和 response mapping 保持在 `src/shared/api` 或 module API layer；不要在 views 中散布 raw requests。
- `Run != Trace`。Trace 是 Observability data，不得用于重建 Run。
- 不要为 `runId`、`traceId`、timestamps、terminal status 或其他 authoritative execution fields 编造值或 fallback。缺失值渲染为 unavailable。
- 保留 nullable evaluation verdicts 和合法的 `score = 0` values。
- 消费 public SSE contract（`type`、`data`、`runId`、terminal events、`[DONE]`）；不要暴露或依赖内部 RuntimeEvent taxonomy。
- 保持 `app / shared / modules` layout。通过 `src/app/modules.tsx` 注册 modules；将 resource-specific API、hooks、types 和 UI 放在一起。

## 关键路径

- `src/app/` — application shell 和 routing。
- `src/shared/api/` — HTTP client、contracts、errors 和 query setup。
- `src/shared/agent-trace/` — shared Trace presentation contracts/components。
- `src/modules/` — feature modules，包括 `runs`、`evaluation`、`ai-chat` 和 management resources。

## 验证

从 `frontend/admin/` 运行：

```bash
npm run check
npm run test
npm run build
```

## 参考

- [根目录 instructions](../../AGENTS.md)
- [FastAPI adapter boundary](../../docs/architecture/fastapi-adapter-boundary.md)
- [Execution Model v2](../../docs/architecture/execution-model-v2.md)
