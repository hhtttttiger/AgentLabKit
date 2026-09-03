# LLM Gateway

`llm_gateway` is the only package permitted to call provider LLM APIs. It owns provider adapters, model resolution, routing/failover, credentials, usage extraction, and gateway-level resilience.

- Consumers depend on `GatewayProtocol` and request models, not provider SDKs or `GatewayService` internals.
- Use `ModelRef` for explicit model selection; preserve default binding behavior when no model is supplied.
- Keep provider-specific behavior in `providers/`; do not duplicate API calls in backend, Runtime, retrieval, memory, or desktop modules.
- Preserve usage and execution identity supplied by callers; the gateway must not become an execution/run owner.

See [root instructions](../../AGENTS.md) and run the targeted gateway tests under `packages/llm_gateway/tests/`.