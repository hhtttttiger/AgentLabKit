from __future__ import annotations

from application.execution.run_projection import RunRecord
from modules.runs.dependencies import get_run_reader


class FakeRunReader:
    def __init__(self, record: RunRecord | None):
        self.record = record
        self.requested: list[str] = []

    async def get_run(self, run_id: str):
        self.requested.append(run_id)
        return self.record if self.record and self.record.run_id == run_id else None


import pytest


@pytest.mark.asyncio
async def test_get_run_contract(app, client, auth_headers):
    record = RunRecord(run_id="run-1", trace_id="trace-1", status="completed", output="")
    reader = FakeRunReader(record)
    app.dependency_overrides[get_run_reader] = lambda: reader
    try:
        response = await client.get("/api/runs/run-1", headers=auth_headers)
    finally:
        app.dependency_overrides.pop(get_run_reader, None)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["runId"] == "run-1"
    assert data["traceId"] == "trace-1"
    assert data["status"] == "completed"
    assert data["output"] == ""
    assert data["durationMs"] is None
    assert data["metadata"] == {}
    assert reader.requested == ["run-1"]


@pytest.mark.asyncio
async def test_get_missing_run_returns_404(app, client, auth_headers):
    reader = FakeRunReader(None)
    app.dependency_overrides[get_run_reader] = lambda: reader
    try:
        response = await client.get("/api/runs/unknown", headers=auth_headers)
    finally:
        app.dependency_overrides.pop(get_run_reader, None)
    assert response.status_code == 404
    assert response.json()["success"] is False
