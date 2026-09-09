# Database migrations

## Compatibility baseline

The repository uses `0001_current_baseline` as the current schema baseline.
Databases created before this baseline are unsupported and are not upgrade-compatible.
Do not edit `alembic_version` to bypass this boundary.

**Decision frozen on 2026-09-09.** The squash window is closed:

- Pre-baseline databases are permanently unsupported. Retaining their data
  requires an explicit export/import procedure, never an Alembic upgrade.
- Re-baselining or re-squashing the chain is prohibited; every schema change
  is a forward revision on top of the baseline.
- `backend/tests/test_migration_chain.py` enforces this on every test pass:
  the baseline is the only root revision, the chain has exactly one head,
  and only the baseline may build schema from ORM metadata.

## Initialize or reset

For a clean database:

```bash
make reset
make up
cd backend
PYTHONPATH=src alembic upgrade head
PYTHONPATH=src python -m bootstrap
```

`make reset` deletes the local PostgreSQL volume. Back up or export any data
that must be retained before resetting. Production environments must use their
normal database replacement/restore procedure.

## Future policy

The baseline is immutable. Future schema changes use real forward revisions
(`0002`, `0003`, ...). Non-additive changes (data transforms, drops, nullability
or uniqueness changes, type changes, or identity/authorization semantics) must
include a non-empty pre-migration fixture and post-migration assertions.

Schema creation belongs to migrations; initial application data belongs to
`bootstrap`.
