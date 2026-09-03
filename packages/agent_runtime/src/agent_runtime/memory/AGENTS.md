<!-- Parent: ../../AGENTS.md -->
# Runtime session memory

此 subtree 管理 single-session context：token-aware trimming、optional summarization、message priority 和 session snapshots。它不同于 cross-session 的 `packages/memory` package。

- 将 context preparation 保持为 pre-execution layer；它不得拥有 execution identity。
- 保留 disabled-memory fallback behavior 和 summary metadata markers。
- 在 `SessionStore` protocol 后面增加 durable stores；不要让 in-memory implementation 依赖 database infrastructure。
- 通过 protocol 使用 `llm_gateway` 进行 summarization。

在 `packages/agent_runtime/tests/` 下运行相关 memory 和 runtime tests。参见 [agent_runtime instructions](../../../AGENTS.md)。
