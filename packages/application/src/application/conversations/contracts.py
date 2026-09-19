from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class Project:
    project_id: str
    name: str
    workspace: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class Conversation:
    conversation_id: str
    project_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


@dataclass(frozen=True)
class ConversationTurn:
    turn_id: str
    conversation_id: str
    role: str
    content: str
    run_id: str | None
    created_at: datetime


class ProjectReader(Protocol):
    async def get_project(self, project_id: str) -> Project | None: ...
    async def list_projects(self) -> list[Project]: ...


class ProjectWriter(Protocol):
    async def create_project(self, project: Project) -> Project: ...
    async def update_project(self, project: Project) -> Project: ...


class ConversationReader(Protocol):
    async def get_conversation(self, conversation_id: str) -> Conversation | None: ...
    async def list_project_conversations(self, project_id: str) -> list[Conversation]: ...
    async def list_turns(self, conversation_id: str, *, limit: int | None = None) -> list[ConversationTurn]: ...


class ConversationWriter(Protocol):
    async def create_conversation(self, conversation: Conversation) -> Conversation: ...
    async def update_conversation(self, conversation: Conversation) -> Conversation: ...
    async def append_turn(self, turn: ConversationTurn) -> ConversationTurn: ...


class ConversationNotFound(LookupError): ...
class ProjectNotFound(LookupError): ...
class InvalidProjectWorkspace(ValueError): ...


@dataclass(frozen=True)
class SendConversationMessageCommand:
    conversation_id: str
    message: str
    user_id: str = "local"
    agent_key: str = "local-agent"
    context_limit: int = 20


@dataclass(frozen=True)
class SendConversationMessageResult:
    conversation: Conversation
    user_turn: ConversationTurn
    assistant_turn: ConversationTurn

