# Agent Turn Streaming Contract

本文档定义 Agent turn 的 public streaming contract。它描述稳定边界，不记录某次接线工作的进度或实现历史。

## Data flow

```text
Client
  → FastAPI SSE adapter
  → ExecuteAgent
  → Agent Runtime
```

FastAPI route 负责请求验证、授权、调用 `ExecuteAgent`，并将 application execution updates 映射为 public SSE。Runtime owns execution facts and identity；adapter 不暴露内部 RuntimeEvent taxonomy。

## Public SSE contract

每条正常事件以 SSE `data:` frame 发送；JSON payload 至少包含：

```text
data: {"type":"context | reply_delta | completed | tool_call | tool_result | delegation_delta | handoff | error", "runId":"runtime-owned-run-id", ...}
```

`data` 是 SSE frame field，不是额外嵌套的 JSON object。当前 adapter 将 public fields（包括 `sessionId`、`traceId`、`agentKey`、`agentVersion` 以及事件类型对应的 payload）放在同一 JSON payload 中。客户端必须将缺失的 authoritative fields 渲染为 unavailable，不得编造或 fallback identity。

常见事件语义包括：

- `context`：turn context，例如 applied skills。
- `reply_delta`：增量回复。
- `completed`：回复完成，包含 reply、usage 和 succeeded status。
- `tool_call` / `tool_result`：工具调用及结果。
- `delegation_delta` / `handoff`：多 Agent 事件。
- `error`：Runtime error 的 public failure mapping。

## Terminal semantics

- 成功完成或失败事件后，stream 必须发送 `data: [DONE]`。
- Runtime error 由 adapter 映射为 `error` 事件；它不是内部 `RuntimeEvent` 的直接透传。
- `[DONE]` 是 stream terminator，不是一个带 JSON payload 的 execution event。
- 一个真实执行的 lifecycle 仍由 Runtime 保证恰好一个 terminal Run event；SSE terminator 不创建新的 Run 或 Trace。

## Layer separation

```text
RuntimeEvent → Application ExecutionUpdate → Public SSE Event
```

这三者不是同一个 contract：RuntimeEvent 是 Runtime execution fact，Application ExecutionUpdate 携带 use-case 的结果与 identity，Public SSE Event 是面向客户端的稳定 DTO。HTTP adapters 和 frontend 只依赖 public SSE contract，不从日志、工具名称或展示文本推断 execution facts。

## Related contracts

- [Execution Model v2](execution-model-v2.md)
- [FastAPI adapter boundary](fastapi-adapter-boundary.md)
