from __future__ import annotations

from application.execution.run_projection import RunRecord
from modules.runs.dependencies import get_capture_run_as_dataset_example, get_replay_run, get_run_reader
from modules.runs.schemas import agent_run_to_response, run_record_to_response


class FakeReplay:
    def __init__(self, result):
        self.result = result
        self.command = None

    async def execute(self, command):
        self.command = command
        return self.result


class FakeCapture:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.command = None
        self.calls = 0

    async def execute(self, command):
        self.calls += 1
        self.command = command
        if self.error is not None:
            raise self.error
        return self.result


class FakeRunReader:
    def __init__(self, record: RunRecord | None):
        self.record = record
        self.requested: list[str] = []

    async def get_run(self, run_id: str):
        self.requested.append(run_id)
        return self.record if self.record and self.record.run_id == run_id else None

    async def list_runs(self, *, user_id: str, limit: int, offset: int = 0):
        if self.record is None or self.record.user_id != user_id:
            return []
        return [self.record][offset:offset + limit]

    async def count_runs(self, *, user_id: str):
        return int(self.record is not None and self.record.user_id == user_id)


import pytest


@pytest.mark.asyncio
async def test_capture_endpoint_returns_public_contract_and_builds_command(app, client, auth_headers):
    from evaluation.contracts_v2 import DatasetExample
    from application.dataset.save_run_as_example import CaptureRunAsDatasetExampleResult

    reader = FakeRunReader(RunRecord(
        run_id="run-1", trace_id="trace-1", user_id="test-user", status="completed", output="actual",
    ))
    capture = FakeCapture(CaptureRunAsDatasetExampleResult(
        dataset_id="dataset-1",
        source_run_id="run-1",
        example=DatasetExample(example_id="example-1", dataset_id="dataset-1", input_text="hello"),
    ))
    app.dependency_overrides[get_run_reader] = lambda: reader
    app.dependency_overrides[get_capture_run_as_dataset_example] = lambda: capture
    try:
        response = await client.post(
            "/api/runs/run-1/capture",
            json={"datasetId": 7, "expectedOutput": "golden", "metadata": {}},
            headers=auth_headers,
        )
    finally:
        app.dependency_overrides.pop(get_capture_run_as_dataset_example, None)
        app.dependency_overrides.pop(get_run_reader, None)

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "msg": "ok",
        "data": {"datasetId": "dataset-1", "sourceRunId": "run-1", "exampleId": "example-1"},
    }
    assert capture.calls == 1
    assert capture.command.dataset_id == "7"
    assert capture.command.run_id == "run-1"
    assert capture.command.expected_output == "golden"
    assert capture.command.metadata == {}


@pytest.mark.asyncio
async def test_capture_preserves_null_and_falsey_expected_output(app, client, auth_headers):
    from evaluation.contracts_v2 import DatasetExample
    from application.dataset.save_run_as_example import CaptureRunAsDatasetExampleResult

    reader = FakeRunReader(RunRecord(run_id="run-1", user_id="test-user", status="completed"))
    capture = FakeCapture(CaptureRunAsDatasetExampleResult(
        dataset_id="7", source_run_id="run-1",
        example=DatasetExample(example_id="example-1", dataset_id="7", input_text="hello"),
    ))
    app.dependency_overrides.update({get_run_reader: lambda: reader, get_capture_run_as_dataset_example: lambda: capture})
    try:
        await client.post("/api/runs/run-1/capture", json={"datasetId": 7, "expectedOutput": ""}, headers=auth_headers)
        assert capture.command.expected_output == ""
        await client.post("/api/runs/run-1/capture", json={"datasetId": 7, "expectedOutput": None}, headers=auth_headers)
        assert capture.command.expected_output is None
        await client.post("/api/runs/run-1/capture", json={"datasetId": 7}, headers=auth_headers)
        assert capture.command.expected_output is None
    finally:
        app.dependency_overrides.pop(get_capture_run_as_dataset_example, None)
        app.dependency_overrides.pop(get_run_reader, None)


@pytest.mark.asyncio
async def test_capture_hides_non_owner_and_null_owner(app, client, auth_headers, make_token):
    for user_id, headers in (("user-a", {"Authorization": f"Bearer {make_token('user-b')}"}), (None, auth_headers)):
        reader = FakeRunReader(RunRecord(run_id="run-1", user_id=user_id, status="completed"))
        capture = FakeCapture()
        app.dependency_overrides.update({get_run_reader: lambda: reader, get_capture_run_as_dataset_example: lambda: capture})
        try:
            response = await client.post("/api/runs/run-1/capture", json={"datasetId": 7}, headers=headers)
        finally:
            app.dependency_overrides.pop(get_capture_run_as_dataset_example, None)
            app.dependency_overrides.pop(get_run_reader, None)
        assert response.status_code == 404
        assert capture.calls == 0


@pytest.mark.asyncio
async def test_capture_maps_missing_dataset_to_not_found(app, client, auth_headers):
    from common.errors import NotFoundError

    reader = FakeRunReader(RunRecord(run_id="run-1", user_id="test-user", status="completed"))
    capture = FakeCapture(error=NotFoundError("Dataset", "missing"))
    app.dependency_overrides.update({get_run_reader: lambda: reader, get_capture_run_as_dataset_example: lambda: capture})
    try:
        response = await client.post("/api/runs/run-1/capture", json={"datasetId": 999}, headers=auth_headers)
    finally:
        app.dependency_overrides.pop(get_capture_run_as_dataset_example, None)
        app.dependency_overrides.pop(get_run_reader, None)
    assert response.status_code == 404
    assert response.json()["success"] is False


@pytest.mark.asyncio
async def test_capture_rejects_missing_and_non_capturable_runs(app, client, auth_headers):
    from application.dataset.save_run_as_example import RunNotCapturable

    for record, expected_status in [
        (None, 404),
        (RunRecord(run_id="run-1", user_id="test-user", status="running"), 409),
        (RunRecord(run_id="run-1", user_id="test-user", status="failed"), 409),
        (RunRecord(run_id="run-1", user_id="test-user", status="cancelled"), 409),
    ]:
        reader = FakeRunReader(record)
        capture = FakeCapture(error=RunNotCapturable("not capturable"))
        app.dependency_overrides.update({get_run_reader: lambda: reader, get_capture_run_as_dataset_example: lambda: capture})
        try:
            response = await client.post("/api/runs/run-1/capture", json={"datasetId": 7}, headers=auth_headers)
        finally:
            app.dependency_overrides.pop(get_capture_run_as_dataset_example, None)
            app.dependency_overrides.pop(get_run_reader, None)
        assert response.status_code == expected_status
        if record is None:
            assert capture.calls == 0


@pytest.mark.asyncio
async def test_list_runs_is_owner_scoped_and_preserves_identity(app, client, auth_headers):
    reader = FakeRunReader(RunRecord(run_id="run-1", trace_id="trace-1", user_id="test-user", status="completed", target_key="support"))
    app.dependency_overrides[get_run_reader] = lambda: reader
    try:
        response = await client.get("/api/runs?limit=10", headers=auth_headers)
    finally:
        app.dependency_overrides.pop(get_run_reader, None)
    assert response.status_code == 200
    assert response.json()["data"] == {"items": [{"runId": "run-1", "traceId": "trace-1", "status": "completed", "targetType": None, "targetKey": "support", "targetVersion": None, "input": None, "output": None, "startedAt": None, "completedAt": None, "durationMs": None, "sessionId": None, "errorCode": None, "errorMessage": None, "metadata": {}}], "total": 1}


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
