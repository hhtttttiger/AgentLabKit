# Database package

`packages/db` provides shared SQLAlchemy base classes, async engine/session lifecycle, and Snowflake IDs. It has no dependency on project packages and remains below domain/application modules in the dependency graph.

- Keep configuration of engine and Snowflake worker identity at the composition root.
- Do not put business services, HTTP concerns, or package-specific orchestration here.
- Preserve shared ORM and ID contracts when changing models; check dependent packages and migrations.

Run the relevant tests under `packages/db/tests/`. See [root instructions](../../AGENTS.md).