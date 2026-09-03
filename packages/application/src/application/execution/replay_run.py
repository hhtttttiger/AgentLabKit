from __future__ import annotations

from typing import Any

from agent_runtime.contracts.run import RunTarget

from ..ports.agents import AgentDefinitionReader
from ..ports.execution import RunExecutor, RunReader
from .contracts import ReplayRunCommand, ReplayRunResult


class ReplayRunError(Exception):
    """Base error for a replay that cannot be started."""


class ReplaySourceNotFound(ReplayRunError):
    pass


class ReplayTargetUnsupported(ReplayRunError):
    pass


class ReplayTargetUnavailable(ReplayRunError):
    pass


class ReplayInputUnavailable(ReplayRunError):
    pass


class ReplayRun:
    """Re-execute authoritative stored Run input through the Runtime.

    This use case never creates an AgentRun itself.  Target identity from the
    durable Run projection is resolved against the current definition reader,
    while the Runtime remains the sole owner of execution identity.
    """

    def __init__(
        self,
        runs: RunReader,
        executor: RunExecutor,
        targets: AgentDefinitionReader | None = None,
    ) -> None:
        self._runs = runs
        self._executor = executor
        self._targets = targets

    async def execute(self, command: ReplayRunCommand) -> ReplayRunResult:
        source = await self._runs.get_run(command.source_run_id)
        if source is None:
            raise ReplaySourceNotFound(command.source_run_id)
        if source.input is None:
            raise ReplayInputUnavailable(command.source_run_id)

        target = await self._resolve_target(source)
        # Caller metadata is not historical execution metadata.  Lineage is
        # authoritative and cannot be spoofed by a same-named caller field.
        metadata = {
            **dict(command.metadata),
            "replay_of_run_id": source.run_id,
        }
        new_run = await self._executor.execute(
            input=source.input,
            target=target,
            session_id=None,  # replay starts an independent execution context
            user_id=command.user_id,
            history=(),
            metadata=metadata,
        )
        return ReplayRunResult(
            source_run_id=source.run_id,
            new_run_id=new_run.run_id,
            run=new_run,
        )

    async def _resolve_target(self, source: Any) -> RunTarget:
        # Compatibility for pre-projection test doubles only. Durable
        # RunRecord values always take the identity-based path below.
        if not hasattr(source, "target_type") and hasattr(source, "target"):
            return source.target

        target_type = source.target_type
        if target_type != "agent":
            raise ReplayTargetUnsupported(
                f"replay does not support target type {target_type!r}"
            )
        if not source.target_key or source.target_version is None:
            raise ReplayTargetUnavailable(
                "historical agent target identity or version is unavailable"
            )
        if self._targets is None:
            raise ReplayTargetUnavailable("agent target resolver is not configured")
        try:
            target = await self._targets.resolve(
                source.target_key, version=str(source.target_version)
            )
        except LookupError as exc:
            raise ReplayTargetUnavailable(str(exc)) from exc
        if target is None:
            raise ReplayTargetUnavailable(
                f"agent {source.target_key} version {source.target_version} is unavailable"
            )
        return target


__all__ = [
    "ReplayInputUnavailable",
    "ReplayRun",
    "ReplayRunError",
    "ReplaySourceNotFound",
    "ReplayTargetUnavailable",
    "ReplayTargetUnsupported",
]
