from datetime import datetime, timezone

import pytest

from agent_runtime.contracts.run import AgentRun, RunTarget
from agent_runtime.events_v2 import RunCancelled, RunCompleted, RunFailed, RunStarted
from application.execution.run_projection import (
    InMemoryRunStore,
    RunProjector,
    RunProjectionConflict,
)


@pytest.fixture
def ids():
    return {"run_id": "run-1", "trace_id": "trace-1"}


@pytest.mark.asyncio
async def test_lifecycle_is_idempotent_and_preserves_distinct_identity(ids):
    store = InMemoryRunStore()
    projector = RunProjector(store)
    started = RunStarted(
        event_id="start-1", **ids, agent_key="support", agent_version="7",
        input_text="hello", session_id="session-1",
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    completed = RunCompleted(
        event_id="done-1", **ids, output_text="", total_duration_ms=0,
        timestamp=datetime(2025, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
    )
    await projector.handle(started)
    await projector.handle(started)
    await projector.handle(completed)
    await projector.handle(completed)

    record = await store.get_run("run-1")
    assert record is not None
    assert record.run_id == "run-1"
    assert record.trace_id == "trace-1"
    assert record.status == "completed"
    assert record.output == ""  # empty is a real Runtime fact
    assert record.duration_ms == 0  # explicit zero is a real Runtime fact


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("event", "status"),
    [
        (RunFailed(run_id="r", trace_id="t", event_id="f", error_code="E", error_message="bad"), "failed"),
        (RunCancelled(run_id="r", trace_id="t", event_id="c", reason="user",), "cancelled"),
    ],
)
async def test_terminal_events(ids, event, status):
    store = InMemoryRunStore()
    await store.project_event(RunStarted(event_id="s", **ids))
    event.run_id, event.trace_id = ids["run_id"], ids["trace_id"]
    await store.project_event(event)
    record = await store.get_run(ids["run_id"])
    assert record.status == status


@pytest.mark.asyncio
async def test_snapshot_is_authoritative_and_preserves_zero_values(ids):
    store = InMemoryRunStore()
    started_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    finished_at = datetime(2025, 1, 1, 0, 0, 2, tzinfo=timezone.utc)
    await store.project_event(RunStarted(event_id="s", timestamp=started_at, **ids))
    run = AgentRun(
        run_id=ids["run_id"], trace_id=ids["trace_id"], input="in", output="",
        target=RunTarget(type="workflow", workflow_id="wf", workflow_version="3"),
        started_at=started_at, finished_at=finished_at,
    )
    run.mark_completed(output="")
    # mark_completed uses a current clock; set the authoritative fixture values.
    run.finished_at = finished_at
    await store.finalize(run)
    record = await store.get_run(ids["run_id"])
    assert record.target_type == "workflow"
    assert record.target_key == "wf"
    assert record.target_version == "3"
    assert record.output == ""
    assert record.duration_ms == 2000


@pytest.mark.asyncio
async def test_orphan_terminal_is_retryable_and_not_marked_applied():
    store = InMemoryRunStore()
    orphan = RunCompleted(event_id="orphan", run_id="r", trace_id="t", output_text="x")
    await store.project_event(orphan)
    assert store.quarantined_events == (orphan,)
    assert "orphan" not in store.applied_event_ids

    await store.project_event(RunStarted(event_id="s", run_id="r", trace_id="t"))
    record = await store.get_run("r")
    assert record.status == "completed"
    assert record.output == "x"
    assert store.quarantined_events == ()
    assert "orphan" in store.applied_event_ids


@pytest.mark.asyncio
async def test_trace_id_conflict_preserves_record():
    store = InMemoryRunStore()
    await store.project_event(RunStarted(event_id="s", run_id="r", trace_id="t1"))
    terminal = RunCompleted(event_id="d", run_id="r", trace_id="t2", output_text="new")
    with pytest.raises(RunProjectionConflict):
        await store.project_event(terminal)
    record = await store.get_run("r")
    assert record.status == "running"
    assert record.trace_id == "t1"
    assert "d" not in store.applied_event_ids


@pytest.mark.asyncio
async def test_snapshot_trace_conflict_preserves_record():
    store = InMemoryRunStore()
    await store.project_event(RunStarted(event_id="s", run_id="r", trace_id="t1"))
    run = AgentRun(run_id="r", trace_id="t2", target=RunTarget(type="agent", agent_key="a"))
    run.mark_completed(output="x")
    with pytest.raises(RunProjectionConflict):
        await store.finalize(run)
    record = await store.get_run("r")
    assert record.trace_id == "t1"
    assert record.status == "running"


@pytest.mark.asyncio
async def test_missing_trace_id_can_be_filled_by_snapshot():
    store = InMemoryRunStore()
    await store.project_event(RunStarted(event_id="s", run_id="r"))
    run = AgentRun(run_id="r", trace_id="t", target=RunTarget(type="agent", agent_key="a"))
    run.mark_completed(output="")
    await store.finalize(run)
    record = await store.get_run("r")
    assert record.trace_id == "t"
    assert record.output == ""


@pytest.mark.asyncio
async def test_conflicting_terminal_is_not_applied():
    store = InMemoryRunStore()
    await store.project_event(RunStarted(event_id="s", run_id="r", trace_id="t"))
    first = RunCompleted(event_id="d1", run_id="r", trace_id="t", output_text="x")
    second = RunFailed(event_id="d2", run_id="r", trace_id="t", error_message="late")
    await store.project_event(first)
    with pytest.raises(RunProjectionConflict):
        await store.project_event(second)
    assert "d2" not in store.applied_event_ids
