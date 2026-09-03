"""Backend adapter contract tests that do not require a running PostgreSQL."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from agent_runtime.events_v2 import RunStarted
from modules.run_projection.models import RunProjectionEventModel, RunRecordModel
from modules.run_projection.store import SqlAlchemyRunStore, _json_safe


def test_run_id_is_the_database_primary_key_and_trace_is_indexed_association():
    table = RunRecordModel.__table__
    assert list(table.primary_key.columns.keys()) == ["run_id"]
    assert table.c.trace_id.primary_key is False
    assert table.c.trace_id.unique is not True
    assert any(
        index.name == "ix_run_records_trace_id"
        and [column.name for column in index.columns] == ["trace_id"]
        for index in table.indexes
    )
    ddl = str(CreateTable(table).compile(dialect=postgresql.dialect()))
    assert "PRIMARY KEY (run_id)" in ddl


def test_projection_event_ledger_has_stable_event_identity():
    assert list(RunProjectionEventModel.__table__.primary_key.columns.keys()) == ["event_id"]


def test_json_projection_preserves_empty_and_zero_values():
    value = {"zero": 0, "false": False, "empty": "", "list": [], "object": {}}
    assert _json_safe(value) == value
    assert _json_safe(datetime(2025, 1, 1, tzinfo=timezone.utc)) == "2025-01-01T00:00:00+00:00"


def test_json_projection_fails_loudly_for_unknown_objects():
    with pytest.raises(TypeError, match="not JSON serializable"):
        _json_safe(object())


@pytest.mark.asyncio
async def test_started_projection_persists_owner():
    class Result:
        def scalar_one_or_none(self):
            return "start-1"

    class Transaction:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    class Session:
        def __init__(self):
            self.added = None

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        def begin(self):
            return Transaction()

        async def execute(self, statement):
            return Result()

        async def get(self, model, run_id, **kwargs):
            return None

        def add(self, model):
            self.added = model

    session = Session()
    store = SqlAlchemyRunStore(lambda: session)
    await store.project_event(RunStarted(
        event_id="start-1", run_id="run-1", trace_id="trace-1", user_id="user-a",
    ))
    assert session.added.user_id == "user-a"
    assert session.added.status == "running"
