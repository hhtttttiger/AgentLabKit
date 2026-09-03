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


def to_run_response(record: Any) -> RunResponse:
    """Map the internal RunRecord explicitly; no fallback or reconstruction."""

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
