from __future__ import annotations

from ..ports.agents import AgentDefinitionReader
from ..ports.execution import RunExecutor
from .contracts import ExecuteAgentCommand, ExecuteAgentResult, ExecuteAgentUpdate

class ExecuteAgent:
    """Coordinate agent resolution and a real Runtime execution."""
    def __init__(self, executor: RunExecutor, agents: AgentDefinitionReader) -> None:
        self._executor = executor
        self._agents = agents

    async def execute(self, command: ExecuteAgentCommand) -> ExecuteAgentResult:
        target = await self._agents.resolve(command.agent_key)
        run = await self._executor.execute(
            input=command.input,
            target=target,
            session_id=command.session_id,
            user_id=command.user_id,
            history=command.history,
            metadata=command.metadata,
        )
        return ExecuteAgentResult(run=run)

    async def stream(self, command: ExecuteAgentCommand):
        target = await self._agents.resolve(command.agent_key)
        async for update in self._executor.stream(
            input=command.input,
            target=target,
            session_id=command.session_id,
            user_id=command.user_id,
            history=command.history,
            metadata=command.metadata,
        ):
            yield update
