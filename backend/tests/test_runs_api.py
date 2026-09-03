from __future__ import annotations

from application.execution.run_projection import RunRecord
from modules.runs.dependencies import get_replay_run, get_run_reader
from modules.runs.schemas import agent_run_to_response, run_record_to_response


class FakeReplay:
    def __init__(self, result):
        self.result = result
        self.command = None

    async def execute(self, command):
        self.command = command
        return self.result


class FakeRunReader:
    def __init__(self, record: RunRecord | None):
        self.record = record
        self.requested: list[str] = []

    async def get_run(self, run_id: str):
        self.requested.append(run_id)
        return self.record if self.record and self.record.run_id == run_id else None


import pytest


@pytest.mark.asyncio
async def test_get_running_run_is_visible_to_owner(app, client, auth_headers):
    record = RunRecord(run_id="run-1", trace_id="trace-1", user_id="test-user", status="running", output="")
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
    assert data["status"] == "running"
    assert data["output"] == ""
    assert data["durationMs"] is None
    assert data["metadata"] == {}
    assert reader.requested == ["run-1"]


@pytest.mark.asyncio
async def test_replay_endpoint_is_thin_and_returns_new_run(app, client, auth_headers):
    from agent_runtime.contracts.run import AgentRun, RunStatus, RunTarget
    from application.execution import ReplayRunResult

    reader = FakeRunReader(RunRecord(run_id="source-1", user_id="test-user", status="completed", input="hello"))
    app.dependency_overrides[get_run_reader] = lambda: reader
    replay = FakeReplay(ReplayRunResult(
        source_run_id="source-1",
        new_run_id="new-1",
        run=AgentRun(
            run_id="new-1", trace_id="trace-new", input={}, output="ok",
            status=RunStatus.COMPLETED,
            target=RunTarget(type="agent", agent_key="support", agent_version="3"),
        ),
    ))
    app.dependency_overrides[get_replay_run] = lambda: replay
    try:
        response = await client.post(
            "/api/runs/source-1/replay",
            json={"metadata": {"request_id": "r1"}},
            headers=auth_headers,
        )
    finally:
        app.dependency_overrides.pop(get_replay_run, None)
        app.dependency_overrides.pop(get_run_reader, None)
    assert response.status_code == 200
    assert response.json()["data"]["sourceRunId"] == "source-1"
    assert response.json()["data"]["run"]["runId"] == "new-1"
    assert replay.command.source_run_id == "source-1"
    assert replay.command.user_id == "test-user"
    assert replay.command.metadata == {"request_id": "r1"}


@pytest.mark.asyncio
async def test_non_owner_running_run_is_hidden(app, client, auth_headers):
    reader = FakeRunReader(RunRecord(run_id="run-1", user_id="other-user", status="running"))
    app.dependency_overrides[get_run_reader] = lambda: reader
    try:
        response = await client.get("/api/runs/run-1", headers=auth_headers)
    finally:
        app.dependency_overrides.pop(get_run_reader, None)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_replay_non_owner_run_is_hidden(app, client, auth_headers):
    reader = FakeRunReader(RunRecord(run_id="source-1", user_id="other-user", status="completed", input="hello"))
    app.dependency_overrides[get_run_reader] = lambda: reader
    app.dependency_overrides[get_replay_run] = lambda: FakeReplay(None)
    try:
        response = await client.post("/api/runs/source-1/replay", headers=auth_headers)
    finally:
        app.dependency_overrides.pop(get_run_reader, None)
        app.dependency_overrides.pop(get_replay_run, None)
    assert response.status_code == 404


def test_run_response_mappers_are_explicit_and_preserve_empty_values():
    from agent_runtime.contracts.run import AgentRun, RunStatus, RunTarget
    from typing import get_type_hints

    record = RunRecord(run_id="record", status="completed", output="", duration_ms=0)
    mapped_record = run_record_to_response(record)
    assert mapped_record.output == ""
    assert mapped_record.duration_ms == 0

    run = AgentRun(
        run_id="runtime", status=RunStatus.FAILED,
        target=RunTarget(type="agent", agent_key="support", agent_version="2"),
    )
    mapped_run = agent_run_to_response(run)
    assert mapped_run.status == "failed"
    assert mapped_run.target_type == "agent"
    assert mapped_run.target_key == "support"
    assert mapped_run.target_version == "2"
    assert get_type_hints(run_record_to_response)["record"] is RunRecord
    assert get_type_hints(agent_run_to_response)["run"] is AgentRun


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
