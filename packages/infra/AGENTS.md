# Infrastructure package

`packages/infra` 是最低层的 Redis、cache 和 queue package。它不得依赖 application、backend、Runtime 或其他 project packages。

- 将 Redis lifecycle、cache backends 和 queue protocols 保持在此 package 的 interfaces 后面。
- 测试使用 `InMemoryCache`/`InMemoryQueue`；将 Redis-specific behavior 保持在 Redis implementations 中。
- Queue consumers 负责 ack/nack/retry behavior；payload schemas 应由调用它们的 module 记录，而不是放在这里。
- 不要在 infrastructure 中放置 business orchestration 或 HTTP behavior。

修改后运行 `packages/infra/tests/` 下的相关 tests。参见 [根目录 instructions](../../AGENTS.md)。
