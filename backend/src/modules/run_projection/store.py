from __future__ import annotations

import logging
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from application.execution.run_projection import (
    RunProjectionConflict,
    RunReader,
    RunRecord,
    RunWriter,
)
from agent_runtime.contracts.run import AgentRun
from agent_runtime.events_v2 import RunCancelled, RunCompleted, RunFailed, RunStarted, RuntimeEvent

from .models import RunProjectionEventModel, RunRecordModel

logger = logging.getLogger(__name__)


def _json_safe(value: Any) -> Any:
    """Normalize the deliberately JSON-shaped Run payload contract.

    Unknown objects fail loudly rather than becoming ``repr``/pickle data.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return _json_safe(value.value)
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    raise TypeError(f"Run payload is not JSON serializable: {type(value).__name__}")


class SqlAlchemyRunStore(RunReader, RunWriter):
    """Durable adapter for the framework-neutral Run projection contracts."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def get_run(self, run_id: str) -> RunRecord | None:
        async with self._session_factory() as session:
            model = await session.get(RunRecordModel, run_id)
            return self._to_record(model) if model is not None else None

    async def project_event(self, event: RuntimeEvent) -> None:
        event_id = getattr(event, "event_id", "")
        if not event_id or not event.run_id:
            logger.warning("run_projection.malformed_event event_type=%s", getattr(event, "event_type", None))
            return
        async with self._session_factory() as session:
            async with session.begin():
                # Claiming the authoritative Runtime event id and the row
                # transition in one transaction makes redelivery idempotent.
                claimed = await session.execute(
                    insert(RunProjectionEventModel)
                    .values(event_id=event_id, run_id=event.run_id,
                            event_type=event.event_type, applied_at=_utc_now())
                    .on_conflict_do_nothing(index_elements=[RunProjectionEventModel.event_id])
                    .returning(RunProjectionEventModel.event_id)
                )
                if claimed.scalar_one_or_none() is None:
                    return
                model = await session.get(RunRecordModel, event.run_id, with_for_update=True)
                if isinstance(event, RunStarted):
                    if model is not None:
                        if model.trace_id and event.trace_id and model.trace_id != event.trace_id:
                            raise RunProjectionConflict(f"run_id {event.run_id} has conflicting trace_id")
                    else:
                        session.add(RunRecordModel(
                            run_id=event.run_id,
                            trace_id=event.trace_id or None,
                            status="running",
                            target_key=event.agent_key or None,
                            target_version=str(event.agent_version) if event.agent_version else None,
                            input_json=_json_safe(event.input_text),
                            started_at=event.timestamp,
                            session_id=event.session_id or None,
                            metadata_json=_json_safe(dict(event.attributes)),
                            projected_at=event.timestamp,
                            updated_at=event.timestamp,
                            projection_version=1,
                        ))
                elif isinstance(event, (RunCompleted, RunFailed, RunCancelled)):
                    if model is None:
                        raise RunProjectionConflict(f"orphan terminal for run_id {event.run_id}")
                    self._project_terminal(model, event)
                # Non-lifecycle events do not affect Run v1.

    async def finalize(self, run: AgentRun) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                model = await session.get(RunRecordModel, run.run_id, with_for_update=True)
                if model is None:
                    logger.warning("run_projection.orphan_snapshot run_id=%s", run.run_id)
                    return
                status = run.status.value
                if model.status != "running" and model.status != status:
                    raise RunProjectionConflict(f"run_id {run.run_id} snapshot changes terminal status")
                if model.trace_id and run.trace_id and model.trace_id != run.trace_id:
                    raise RunProjectionConflict(f"run_id {run.run_id} has conflicting trace_id")
                model.trace_id = model.trace_id or run.trace_id
                model.status = status
                model.target_type = run.target.type if run.target.type is not None else model.target_type
                key = run.target.agent_key if run.target.agent_key is not None else run.target.workflow_id
                version = run.target.agent_version if run.target.agent_version is not None else run.target.workflow_version
                if key is not None:
                    model.target_key = key
                if version is not None:
                    model.target_version = version
                model.input_json = _json_safe(run.input)
                model.output_json = _json_safe(run.output)
                model.started_at = run.started_at
                model.completed_at = run.finished_at
                model.duration_ms = run.duration_ms
                if run.session_id is not None:
                    model.session_id = run.session_id
                model.metadata_json = _json_safe(run.metadata)
                model.error_code = run.error.code if run.error is not None else None
                model.error_message = run.error.message if run.error is not None else None
                model.updated_at = _utc_now()

    @staticmethod
    def _project_terminal(model: RunRecordModel, event: RunCompleted | RunFailed | RunCancelled) -> None:
        if model.trace_id and event.trace_id and model.trace_id != event.trace_id:
            raise RunProjectionConflict(f"run_id {event.run_id} has conflicting trace_id")
        if model.trace_id is None and event.trace_id:
            model.trace_id = event.trace_id
        if model.status != "running":
            expected = (model.status, model.output_json, model.error_code, model.error_message, model.completed_at)
            actual = ("completed" if isinstance(event, RunCompleted) else "failed" if isinstance(event, RunFailed) else "cancelled",
                      event.output_text if isinstance(event, RunCompleted) else None,
                      event.error_code or None if isinstance(event, RunFailed) else None,
                      event.error_message or None if isinstance(event, RunFailed) else None, event.timestamp)
            if expected != actual:
                raise RunProjectionConflict(f"run_id {event.run_id} has conflicting terminal facts")
            return
        model.status = "completed" if isinstance(event, RunCompleted) else "failed" if isinstance(event, RunFailed) else "cancelled"
        model.completed_at = event.timestamp
        model.updated_at = event.timestamp
        if isinstance(event, RunCompleted):
            model.output_json = _json_safe(event.output_text)
            model.metadata_json = {**(model.metadata_json or {}), **_json_safe(event.attributes)}
            model.duration_ms = event.total_duration_ms
        elif isinstance(event, RunFailed):
            model.error_code = event.error_code or None
            model.error_message = event.error_message or None
        elif event.reason:
            model.metadata_json = {**(model.metadata_json or {}), "cancel_reason": event.reason}

    @staticmethod
    def _to_record(model: RunRecordModel) -> RunRecord:
        return RunRecord(run_id=model.run_id, trace_id=model.trace_id, status=model.status,
            target_type=model.target_type, target_key=model.target_key, target_version=model.target_version,
            input=model.input_json, output=model.output_json, started_at=model.started_at,
            completed_at=model.completed_at, duration_ms=model.duration_ms, session_id=model.session_id,
            error_code=model.error_code, error_message=model.error_message,
            metadata=dict(model.metadata_json or {}), projected_at=model.projected_at,
            updated_at=model.updated_at, projection_version=model.projection_version)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

