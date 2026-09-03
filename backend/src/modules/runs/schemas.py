from __future__ import annotations

from datetime import datetime
from typing import Any

from agent_runtime.contracts.run import AgentRun
from application.execution.run_projection import RunRecord
from pydantic import Field

from common.schemas import CamelModel


class CaptureRunRequest(CamelModel):
    """Transport input for the Run -> DatasetExample action."""

    dataset_id: int
    expected_output: Any | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CaptureRunResponse(CamelModel):
    dataset_id: str
    source_run_id: str
    example_id: str


class CaptureRunResponseEnvelope(CamelModel):
    success: bool
    msg: str
    data: CaptureRunResponse


class RunResponse(CamelModel):
    """Public projection of the durable Runtime Run record."""

    run_id: str
    trace_id: str | None = None
    status: str
    target_type: str | None = None
    target_key: str | None = None
    target_version: str | None = None
    input: Any = None
    output: Any = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    session_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunResponseEnvelope(CamelModel):
    success: bool
    msg: str
    data: RunResponse


class RunListResponse(CamelModel):
    items: list[RunResponse]
    total: int


class RunListResponseEnvelope(CamelModel):
    success: bool
    msg: str
    data: RunListResponse


class ReplayRunRequest(CamelModel):
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReplayRunResponse(CamelModel):
    source_run_id: str
    run: RunResponse


class ReplayRunResponseEnvelope(CamelModel):
    success: bool
    msg: str
    data: ReplayRunResponse


def run_record_to_response(record: RunRecord) -> RunResponse:
    """Mechanically map the durable Run projection to its transport DTO."""
    return RunResponse(
        run_id=record.run_id,
        trace_id=record.trace_id,
        status=record.status,
        target_type=record.target_type,
        target_key=record.target_key,
        target_version=record.target_version,
        input=record.input,
        output=record.output,
        started_at=record.started_at,
        completed_at=record.completed_at,
        duration_ms=record.duration_ms,
        session_id=record.session_id,
        error_code=record.error_code,
        error_message=record.error_message,
        metadata=dict(record.metadata),
    )


def agent_run_to_response(run: AgentRun) -> RunResponse:
    """Mechanically map a Runtime result without reading the durable store."""
    target = run.target
    target_key = target.agent_key if target.agent_key is not None else target.workflow_id
    target_version = target.agent_version if target.agent_version is not None else target.workflow_version
    return RunResponse(
        run_id=run.run_id,
        trace_id=run.trace_id,
        status=run.status.value,
        target_type=target.type,
        target_key=target_key,
        target_version=target_version,
        input=run.input,
        output=run.output,
        started_at=run.started_at,
        completed_at=run.finished_at,
        duration_ms=run.duration_ms,
        session_id=run.session_id,
        error_code=run.error.code if run.error is not None else None,
        error_message=run.error.message if run.error is not None else None,
        metadata=dict(run.metadata),
    )
