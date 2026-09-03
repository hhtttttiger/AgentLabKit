# Database package

`packages/db` 提供共享 SQLAlchemy base classes、async engine/session lifecycle 和 Snowflake IDs。它不依赖 project packages，并在 dependency graph 中位于 domain/application modules 之下。

- 将 engine 和 Snowflake worker identity 的 configuration 保持在 composition root。
- 不要在这里放置 business services、HTTP concerns 或 package-specific orchestration。
- 修改 models 时保留 shared ORM 和 ID contracts；检查 dependent packages 和 migrations。

在 `packages/db/tests/` 下运行相关 tests。参见 [根目录 instructions](../../AGENTS.md)。
