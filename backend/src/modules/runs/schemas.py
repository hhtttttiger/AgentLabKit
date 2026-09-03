from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from common.schemas import CamelModel


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


class ReplayRunRequest(CamelModel):
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReplayRunResponse(CamelModel):
    source_run_id: str
    run: RunResponse


class ReplayRunResponseEnvelope(CamelModel):
    success: bool
    msg: str
    data: ReplayRunResponse


def to_run_response(record: Any) -> RunResponse:
    """Map either a durable RunRecord or the Runtime's newly returned AgentRun."""
    target = getattr(record, "target", None)
    target_type = getattr(record, "target_type", None)
    target_key = getattr(record, "target_key", None)
    target_version = getattr(record, "target_version", None)
    if target is not None:
        target_type = target_type or target.type
        target_key = target_key or target.agent_key or target.workflow_id
        target_version = target_version or target.agent_version or target.workflow_version
    error = getattr(record, "error", None)
    return RunResponse(
        run_id=record.run_id,
        trace_id=record.trace_id,
        status=record.status.value if hasattr(record.status, "value") else record.status,
        target_type=target_type,
        target_key=target_key,
        target_version=target_version,
        input=record.input,
        output=record.output,
        started_at=record.started_at,
        completed_at=getattr(record, "completed_at", None) or getattr(record, "finished_at", None),
        duration_ms=getattr(record, "duration_ms", None),
        session_id=record.session_id,
        error_code=getattr(record, "error_code", None) or (error.code if error else None),
        error_message=getattr(record, "error_message", None) or (error.message if error else None),
        metadata=dict(record.metadata),
    )
