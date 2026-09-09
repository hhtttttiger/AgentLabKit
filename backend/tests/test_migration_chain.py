"""Enforce the frozen migration chain discipline.

The destructive baseline decision (see docs/operations/database-migrations.md)
was frozen on 2026-09-09. These checks run on every test pass so a second
squash or an accidental branch cannot land silently. They inspect revision
metadata only and need no database.
"""
from __future__ import annotations

from pathlib import Path

from alembic.script import ScriptDirectory

BASELINE_REVISION = "0001_current_baseline"


def _script_directory() -> ScriptDirectory:
    backend = Path(__file__).parents[1]
    return ScriptDirectory(str(backend / "alembic"))


def test_single_base_is_frozen_baseline() -> None:
    bases = [r.revision for r in _script_directory().walk_revisions() if r.is_base]
    assert bases == [BASELINE_REVISION], (
        "The migration baseline is frozen: pre-baseline databases are permanently"
        " unsupported and re-baselining is prohibited. Add a forward revision"
        " (0002, 0003, ...) instead of a new root."
    )


def test_migration_chain_has_single_head() -> None:
    heads = _script_directory().get_heads()
    assert len(heads) == 1, (
        f"Migration chain branched (heads: {heads}). The frozen policy expects one"
        " linear head; resolve branches before merging, not by re-baselining."
    )


def test_only_baseline_builds_schema_from_metadata() -> None:
    for revision in _script_directory().walk_revisions():
        source = Path(revision.path).read_text(encoding="utf-8")
        if revision.revision == BASELINE_REVISION:
            assert "metadata.create_all" in source
        else:
            assert "metadata.create_all" not in source and "metadata.drop_all" not in source, (
                f"Revision {revision.revision} rebuilds schema from ORM metadata;"
                " that pattern is reserved for the frozen baseline. Express the"
                " change as DDL operations on top of the baseline."
            )
