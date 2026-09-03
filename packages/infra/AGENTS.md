# Infrastructure package

`packages/infra` is the lowest-level Redis, cache, and queue package. It must not depend on application, backend, Runtime, or other project packages.

- Keep Redis lifecycle, cache backends, and queue protocols behind this package’s interfaces.
- Use `InMemoryCache`/`InMemoryQueue` for tests; keep Redis-specific behavior in Redis implementations.
- Queue consumers own ack/nack/retry behavior; document payload schemas in their calling module, not here.
- Do not place business orchestration or HTTP behavior in infrastructure.

Run the relevant tests under `packages/infra/tests/` after changes. See [root instructions](../../AGENTS.md).