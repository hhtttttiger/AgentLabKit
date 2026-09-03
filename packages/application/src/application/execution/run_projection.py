"""Framework-neutral durable Run projection boundary.

This module deliberately contains no database or HTTP code.  It defines the
small read-side contract and a reference in-memory implementation used to
characterize projection semantics before a backend storage adapter is added.
RuntimeEvent values are facts; this projector never creates execution identity
or derives missing lifecycle facts.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from agent_runtime.contracts.run import AgentRun
from agent_runtime.events_v2 import (
    RunCancelled,
    RunCompleted,
    RunFailed,
    RunStarted,
    RuntimeEvent,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RunRecord:
    """Minimal Run read model made only from authoritative Runtime facts."""

    run_id: str
    trace_id: str | None = None
    user_id: str | None = None
    status: str = "running"
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
    metadata: dict[str, Any] = field(default_factory=dict)
    projected_at: datetime | None = None
    updated_at: datetime | None = None
    projection_version: int = 1


class RunReader(Protocol):
    async def get_run(self, run_id: str) -> RunRecord | None: ...


class RunWriter(Protocol):
    async def project_event(self, event: RuntimeEvent) -> None: ...
    async def finalize(self, run: AgentRun) -> None: ...


class RunProjectionConflict(ValueError):
    """A duplicate terminal delivery disagrees with an existing terminal fact."""


class InMemoryRunStore(RunReader, RunWriter):
    """Reference store for tests and local composition.

    It models the guarantees a durable adapter must preserve: event-id
    idempotency, one terminal transition, and no identity/timestamp invention.
    A terminal event without a start is quarantined (logged and ignored), not
    turned into a synthetic Run.
    """

    def __init__(self) -> None:
        self._records: dict[str, RunRecord] = {}
        self._applied_event_ids: set[str] = set()
        self._quarantined: dict[str, RuntimeEvent] = {}

    async def get_run(self, run_id: str) -> RunRecord | None:
        return self._records.get(run_id)

    async def project_event(self, event: RuntimeEvent) -> None:
        event_id = getattr(event, "event_id", "")
        if not event_id or not event.run_id:
            logger.warning("run_projection.malformed_event event_type=%s", getattr(event, "event_type", None))
            return
        if event_id in self._applied_event_ids:
            return

        if isinstance(event, RunStarted):
            self._project_started(event)
            # A terminal can be delivered before its start.  Quarantine is a
            # retryable projection state, not successful application.
            for orphan_id, orphan in tuple(self._quarantined.items()):
                if orphan.run_id != event.run_id:
                    continue
                self._project_terminal(orphan)
                self._quarantined.pop(orphan_id, None)
                self._applied_event_ids.add(orphan_id)
        elif isinstance(event, (RunCompleted, RunFailed, RunCancelled)):
            if not self._project_terminal(event):
                return
        # Non-lifecycle events do not add facts to Run v1.  Only a successful
        # projection is marked applied; conflicts and orphans remain retryable.
        self._applied_event_ids.add(event_id)

    def _project_started(self, event: RunStarted) -> None:
        existing = self._records.get(event.run_id)
        if existing is not None:
            # A repeated start with a different event id is a delivery anomaly.
            # Never reset a partially projected or terminal record.
            if existing.trace_id != event.trace_id:
                raise RunProjectionConflict(f"run_id {event.run_id} has conflicting trace_id")
            if existing.user_id is not None and event.user_id is not None and existing.user_id != event.user_id:
                raise RunProjectionConflict(f"run_id {event.run_id} has conflicting user_id")
            if existing.user_id is None and event.user_id is not None:
                existing.user_id = event.user_id
            return
        self._records[event.run_id] = RunRecord(
            run_id=event.run_id,
            trace_id=event.trace_id or None,
            status="running",
            target_key=event.agent_key or None,
            target_version=str(event.agent_version) if event.agent_version else None,
            input=event.input_text,
            started_at=event.timestamp,
            session_id=event.session_id or None,
            user_id=event.user_id,
            metadata=dict(event.attributes),
            projected_at=event.timestamp,
            updated_at=event.timestamp,
        )

    def _project_terminal(self, event: RunCompleted | RunFailed | RunCancelled) -> bool:
        record = self._records.get(event.run_id)
        if record is None:
            self._quarantined.setdefault(event.event_id, event)
            logger.warning("run_projection.orphan_terminal run_id=%s", event.run_id)
            return False
        if record.trace_id and event.trace_id and record.trace_id != event.trace_id:
            raise RunProjectionConflict(f"run_id {event.run_id} has conflicting trace_id")
        if record.trace_id is None and event.trace_id:
            record.trace_id = event.trace_id
        if record.status != "running":
            if self._terminal_fingerprint(record) != self._event_fingerprint(event):
                raise RunProjectionConflict(f"run_id {event.run_id} has conflicting terminal facts")
            return True

        record.updated_at = event.timestamp
        record.completed_at = event.timestamp
        if isinstance(event, RunCompleted):
            record.status = "completed"
            # Empty output is a valid authoritative value.
            record.output = event.output_text
            record.metadata.update(event.attributes)
            record.duration_ms = event.total_duration_ms
        elif isinstance(event, RunFailed):
            record.status = "failed"
            record.error_code = event.error_code or None
            record.error_message = event.error_message or None
        else:
            record.status = "cancelled"
            record.metadata.update(event.attributes)
            if event.reason:
                record.metadata["cancel_reason"] = event.reason
        return True

    @staticmethod
    def _terminal_fingerprint(record: RunRecord) -> tuple[Any, ...]:
        return (record.status, record.output, record.error_code, record.error_message, record.completed_at)

    @staticmethod
    def _event_fingerprint(event: RuntimeEvent) -> tuple[Any, ...]:
        if isinstance(event, RunCompleted):
            return ("completed", event.output_text, None, None, event.timestamp)
        if isinstance(event, RunFailed):
            return ("failed", None, event.error_code or None, event.error_message or None, event.timestamp)
        return ("cancelled", None, None, None, event.timestamp)

    async def finalize(self, run: AgentRun) -> None:
        """Apply the complete terminal AgentRun snapshot without inventing facts."""
        record = self._records.get(run.run_id)
        if record is None:
            logger.warning("run_projection.orphan_snapshot run_id=%s", run.run_id)
            return
        if record.status != "running" and record.status != run.status.value:
            raise RunProjectionConflict(f"run_id {run.run_id} snapshot changes terminal status")
        if record.trace_id and run.trace_id and record.trace_id != run.trace_id:
            raise RunProjectionConflict(f"run_id {run.run_id} has conflicting trace_id")
        if record.user_id is not None and run.user_id is not None and record.user_id != run.user_id:
            raise RunProjectionConflict(f"run_id {run.run_id} has conflicting user_id")
        if record.user_id is None and run.user_id is not None:
            record.user_id = run.user_id
        record.status = run.status.value
        if record.trace_id is None and run.trace_id is not None:
            record.trace_id = run.trace_id
        record.target_type = run.target.type if run.target.type is not None else record.target_type
        snapshot_key = run.target.agent_key if run.target.agent_key is not None else run.target.workflow_id
        snapshot_version = run.target.agent_version if run.target.agent_version is not None else run.target.workflow_version
        if snapshot_key is not None:
            record.target_key = snapshot_key
        if snapshot_version is not None:
            record.target_version = snapshot_version
        record.input = run.input
        record.output = run.output
        record.started_at = run.started_at
        record.completed_at = run.finished_at
        record.duration_ms = run.duration_ms
        record.session_id = run.session_id if run.session_id is not None else record.session_id
        record.metadata = dict(run.metadata)
        record.error_code = None
        record.error_message = None
        if run.error is not None:
            record.error_code = run.error.code
            record.error_message = run.error.message
        record.updated_at = run.finished_at if run.finished_at is not None else record.updated_at

    @property
    def quarantined_events(self) -> tuple[RuntimeEvent, ...]:
        return tuple(self._quarantined.values())

    @property
    def applied_event_ids(self) -> frozenset[str]:
        return frozenset(self._applied_event_ids)


class RunProjector:
    """EventBus listener; storage errors are observable and never runtime facts."""

    def __init__(self, writer: RunWriter) -> None:
        self._writer = writer

    async def handle(self, event: RuntimeEvent) -> None:
        await self._writer.project_event(event)


__all__ = ["InMemoryRunStore", "RunProjector", "RunProjectionConflict", "RunReader", "RunRecord", "RunWriter"]
