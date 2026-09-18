"""Application orchestration for replaying a stored Run via an external executor."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

from agent_runtime.contracts.run import AgentRun, RunTarget

from .run_projection import RunReader


class ExternalReplayExecutor(Protocol):
    async def execute(
        self, *, input: str, target: RunTarget, working_directory: str,
        metadata: Mapping[str, object] | None = None,
    ) -> AgentRun: ...


@dataclass(frozen=True)
class ReplayExternalRunCommand:
    source_run_id: str
    agent_id: str
    working_directory: str
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ReplayExternalRunResult:
    source_run_id: str
    run: AgentRun


class ReplayExternalRunError(Exception):
    pass


class ExternalReplaySourceNotFound(ReplayExternalRunError):
    pass


class ExternalReplayInputUnavailable(ReplayExternalRunError):
    pass


class ReplayExternalRun:
    """Create a new Run from immutable stored input without changing source."""

    def __init__(self, runs: RunReader, executor: ExternalReplayExecutor) -> None:
        self._runs = runs
        self._executor = executor

    async def execute(self, command: ReplayExternalRunCommand) -> ReplayExternalRunResult:
        source = await self._runs.get_run(command.source_run_id)
        if source is None:
            raise ExternalReplaySourceNotFound(command.source_run_id)
        if source.input is None:
            raise ExternalReplayInputUnavailable(command.source_run_id)
        metadata = {
            **dict(command.metadata),
            "replay_of_run_id": source.run_id,
            "source_run_id": source.run_id,
        }
        run = await self._executor.execute(
            input=str(source.input),
            target=RunTarget(type="agent", agent_key=command.agent_id),
            working_directory=command.working_directory,
            metadata=metadata,
        )
        return ReplayExternalRunResult(source_run_id=source.run_id, run=run)


__all__ = [
    "ExternalReplayInputUnavailable", "ExternalReplaySourceNotFound",
    "ReplayExternalRun", "ReplayExternalRunCommand", "ReplayExternalRunError",
    "ReplayExternalRunResult",
]
