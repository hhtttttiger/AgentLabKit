# LLM Gateway

`llm_gateway` 是唯一允许调用 provider LLM APIs 的 package。它负责 provider adapters、model resolution、routing/failover、credentials、usage extraction 和 gateway-level resilience。

- Consumers 依赖 `GatewayProtocol` 和 request models，而不是 provider SDKs 或 `GatewayService` internals。
- 使用 `ModelRef` 进行显式 model selection；未提供 model 时保留 default binding behavior。
- 将 provider-specific behavior 保持在 `providers/`；不要在 backend、Runtime、retrieval、memory 或 desktop modules 中重复 API calls。
- 保留 callers 提供的 usage 和 execution identity；gateway 不得成为 execution/run owner。

参见 [根目录 instructions](../../AGENTS.md)，并运行 `packages/llm_gateway/tests/` 下的 targeted gateway tests。
