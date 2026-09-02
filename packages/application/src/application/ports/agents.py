from typing import Protocol

class AgentDefinitionReader(Protocol):
    async def resolve(self, agent_key: str) -> object: ...
