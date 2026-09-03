from collections.abc import AsyncIterator, Mapping
from typing import Any, Protocol

from agent_runtime import AgentMessage
from agent_runtime.contracts.run import AgentRun, RunTarget
from application.execution.run_projection import RunReader

class RunExecutor(Protocol):
    async def execute(
        self, *, input: str, target: RunTarget, session_id: str | None,
        user_id: str | None, history: tuple[AgentMessage, ...],
        metadata: Mapping[str, object],
    ) -> AgentRun: ...

    def stream(
        self, *, input: str, target: RunTarget, session_id: str | None,
        user_id: str | None, history: tuple[AgentMessage, ...],
        metadata: Mapping[str, object],
    ) -> AsyncIterator[Any]: ...
