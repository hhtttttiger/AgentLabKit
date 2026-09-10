"""Adapters from backend runtime wiring to framework-neutral application ports."""
from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from typing import Any
from uuid import uuid4

from agent_runtime import AgentMessage, AgentTurnRequest
from agent_runtime.contracts.run import RunTarget
from application.execution.contracts import ExecuteAgentUpdate


class BackendAgentReader:
    def __init__(self, loader: Any) -> None:
        self._loader = loader

    async def resolve(self, agent_key: str, version: str | None = None) -> RunTarget:
        try:
            requested_version = int(version) if version is not None else None
        except (TypeError, ValueError) as exc:
            raise LookupError(f"agent {agent_key} has invalid version {version!r}") from exc
        snapshot = await self._loader.load(agent_key, requested_version)
        if snapshot is None:
            raise LookupError(f"agent {agent_key} not found or not published")
        return RunTarget(type="agent", agent_key=agent_key, agent_version=str(snapshot.version_number))


class TraceFinalizingExecutor:
    """Evaluation composition seam: execute a candidate Run, then give the
    Observability publisher a bounded chance to hand this process's trace
    envelope to the durable queue before the trace is read.

    This reuses the publisher's own drain primitive (the same one shutdown
    uses) — no polling, no retry loop, and no Evaluation-specific trace
    synchronization.  Redis → worker → storage ingestion stays asynchronous;
    a still-missing trace is composed as truthfully unavailable downstream.
    """

    def __init__(self, executor: Any, publisher: Any, *, timeout_seconds: float = 5.0) -> None:
        self._executor = executor
        self._publisher = publisher
        self._timeout_seconds = timeout_seconds

    async def execute(self, **kwargs: Any) -> Any:
        run = await self._executor.execute(**kwargs)
        if self._publisher is not None:
            try:
                await self._publisher.flush(timeout_seconds=self._timeout_seconds)
            except Exception:
                # Publication handoff is best-effort for evaluation latency;
                # a missed flush surfaces as unavailable trace evidence.
                pass
        return run

    def stream(self, **kwargs: Any) -> AsyncIterator[Any]:
        return self._executor.stream(**kwargs)


class AgentRuntimeExecutor:
    """Translate typed application inputs to the Runtime public request contract."""
    def __init__(self, runtime: Any) -> None:
        self._runtime = runtime

    def _request(
        self, *, input: str, target: RunTarget, session_id: str | None,
        user_id: str | None, history: tuple[AgentMessage, ...],
        metadata: Mapping[str, object],
    ) -> AgentTurnRequest:
        return AgentTurnRequest(
            session_id=session_id or uuid4().hex,
            user_message=input,
            history=list(history),
            user_id=user_id,
            agent_key=target.agent_key,
            agent_version=int(target.agent_version) if target.agent_version else None,
            metadata={key: str(value) for key, value in metadata.items()},
        )

    async def execute(
        self, *, input: str, target: RunTarget, session_id: str | None,
        user_id: str | None, history: tuple[AgentMessage, ...],
        metadata: Mapping[str, object],
    ) -> Any:
        return await self._runtime.run(self._request(
            input=input, target=target, session_id=session_id, user_id=user_id,
            history=history, metadata=metadata,
        ))

    def stream(
        self, *, input: str, target: RunTarget, session_id: str | None,
        user_id: str | None, history: tuple[AgentMessage, ...],
        metadata: Mapping[str, object],
    ) -> AsyncIterator[Any]:
        async def updates() -> AsyncIterator[ExecuteAgentUpdate]:
            async for event in self._runtime.stream(
                self._request(input=input, target=target, session_id=session_id,
                              user_id=user_id, history=history, metadata=metadata)
            ):
                yield ExecuteAgentUpdate(
                    event=event, run_id=event.run_id, trace_id=event.trace_id,
                    target=target,
                )

        return updates()
