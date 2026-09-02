from __future__ import annotations

from typing import Any, AsyncIterator

from ..ports.agents import AgentDefinitionReader
from ..ports.execution import RunExecutor
from .contracts import ExecuteAgentCommand, ExecuteAgentResult

class ExecuteAgent:
    """Coordinate agent resolution and a real Runtime execution."""
    def __init__(self, executor: RunExecutor, agents: AgentDefinitionReader) -> None:
        self._executor = executor
        self._agents = agents

    async def execute(self, command: ExecuteAgentCommand) -> ExecuteAgentResult:
        target = await self._agents.resolve(command.agent_key)
        metadata = dict(command.metadata)
        if command.session_id is not None:
            metadata.setdefault("session_id", command.session_id)
        if command.user_id is not None:
            metadata.setdefault("user_id", command.user_id)
        if command.history:
            metadata.setdefault("history", command.history)
        run = await self._executor.execute(input=command.input, target=target, metadata=metadata)
        return ExecuteAgentResult(run=run)

    async def stream(self, command: ExecuteAgentCommand) -> AsyncIterator[Any]:
        target = await self._agents.resolve(command.agent_key)
        metadata = dict(command.metadata)
        if command.session_id is not None:
            metadata.setdefault("session_id", command.session_id)
        if command.user_id is not None:
            metadata.setdefault("user_id", command.user_id)
        if command.history:
            metadata.setdefault("history", command.history)
        async for update in self._executor.stream(input=command.input, target=target, metadata=metadata):
            yield update
