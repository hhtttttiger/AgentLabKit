"""Adapters from the backend runtime wiring to ``application`` ports.

This module is deliberately the composition boundary: the application package
never imports these backend-specific implementations.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from agent_runtime import AgentMessage, AgentRole, AgentTurnRequest
from agent_runtime.contracts.run import RunTarget


class BackendAgentReader:
    def __init__(self, loader: Any) -> None:
        self._loader = loader

    async def resolve(self, agent_key: str) -> RunTarget:
        snapshot = await self._loader.load(agent_key)
        if snapshot is None:
            raise LookupError(f"agent {agent_key} not found or not published")
        return RunTarget(
            type="agent",
            agent_key=agent_key,
            agent_version=str(snapshot.version_number),
        )


class AgentRuntimeExecutor:
    """Translate an application execution request to ``AgentRuntime.run``."""
    def __init__(self, runtime: Any) -> None:
        self._runtime = runtime

    async def execute(
        self,
        *,
        input: Any,
        target: RunTarget,
        metadata: Mapping[str, Any] | None = None,
    ) -> Any:
        metadata = dict(metadata or {})
        session_id = str(metadata.pop("session_id", "")) or uuid4().hex
        user_id = str(metadata.pop("user_id", "")) or None
        history = [_message_from_item(item) for item in metadata.pop("history", ())]
        version = int(target.agent_version) if target.agent_version else None
        request = AgentTurnRequest(
            session_id=session_id,
            user_message=str(input),
            history=history,
            user_id=user_id,
            agent_key=target.agent_key,
            agent_version=version,
            metadata={key: str(value) for key, value in metadata.items()},
        )
        return await self._runtime.run(request)

    async def stream(
        self,
        *,
        input: Any,
        target: RunTarget,
        metadata: Mapping[str, Any] | None = None,
    ):
        metadata = dict(metadata or {})
        session_id = str(metadata.pop("session_id", "")) or uuid4().hex
        user_id = str(metadata.pop("user_id", "")) or None
        history = [_message_from_item(item) for item in metadata.pop("history", ())]
        request = AgentTurnRequest(
            session_id=session_id,
            user_message=str(input),
            history=history,
            user_id=user_id,
            agent_key=target.agent_key,
            agent_version=int(target.agent_version) if target.agent_version else None,
            metadata={key: str(value) for key, value in metadata.items()},
        )
        async for event in self._runtime.stream_turn(request):
            yield event


def _message_from_item(item: Any) -> AgentMessage:
    role = item.get("Role", item.get("role", "user"))
    content = item.get("Content", item.get("content", ""))
    return AgentMessage(
        role=AgentRole(str(role).lower()),
        content=str(content),
        name=item.get("Name", item.get("name")),
        metadata=dict(item.get("Metadata", item.get("metadata", {})) or {}),
    )
