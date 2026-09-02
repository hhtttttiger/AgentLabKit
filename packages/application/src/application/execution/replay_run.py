from __future__ import annotations

from ..ports.execution import RunExecutor, RunReader
from .contracts import ReplayRunCommand, ReplayRunResult

class ReplayRun:
    """Request a new execution from Runtime using a historical Run as input."""
    def __init__(self, runs: RunReader, executor: RunExecutor) -> None:
        self._runs = runs
        self._executor = executor

    async def execute(self, command: ReplayRunCommand) -> ReplayRunResult:
        source = await self._runs.get_run(command.source_run_id)
        if source is None:
            raise LookupError(f"run {command.source_run_id} not found")
        target = command.target if command.target is not None else source.target
        metadata = {"replay_of_run_id": command.source_run_id, **dict(command.metadata)}
        new_run = await self._executor.execute(input=source.input, target=target, metadata=metadata)
        return ReplayRunResult(
            source_run_id=command.source_run_id,
            new_run_id=new_run.run_id,
            run=new_run,
        )
