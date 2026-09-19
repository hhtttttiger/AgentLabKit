from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from agent_runtime import AgentMessage, AgentRole
from application.execution.contracts import ExecuteAgentCommand

from .contracts import (
    Conversation,
    ConversationNotFound,
    ConversationReader,
    ConversationTurn,
    ConversationWriter,
    InvalidProjectWorkspace,
    Project,
    ProjectNotFound,
    ProjectReader,
    ProjectWriter,
    SendConversationMessageCommand,
    SendConversationMessageResult,
)


def now() -> datetime:
    return datetime.now(timezone.utc)


def _workspace(value: str) -> str:
    path = Path(value).expanduser()
    if not path.exists() or not path.is_dir():
        raise InvalidProjectWorkspace(f"Project workspace does not exist: {value}")
    return str(path.resolve())


class CreateProject:
    def __init__(self, writer: ProjectWriter): self.writer = writer

    async def execute(self, *, name: str, workspace: str) -> Project:
        if not name.strip(): raise ValueError("Project name is required")
        stamp = now()
        return await self.writer.create_project(Project(uuid4().hex, name.strip(), _workspace(workspace), stamp, stamp))


class ListProjects:
    def __init__(self, reader: ProjectReader): self.reader = reader
    async def execute(self) -> list[Project]: return await self.reader.list_projects()


class GetProject:
    def __init__(self, reader: ProjectReader): self.reader = reader
    async def execute(self, project_id: str) -> Project:
        result = await self.reader.get_project(project_id)
        if result is None: raise ProjectNotFound(project_id)
        return result


class UpdateProject:
    def __init__(self, reader: ProjectReader, writer: ProjectWriter): self.reader, self.writer = reader, writer
    async def execute(self, project_id: str, *, name: str | None = None, workspace: str | None = None) -> Project:
        current = await GetProject(self.reader).execute(project_id)
        updated = Project(current.project_id, name.strip() if name is not None else current.name,
                          _workspace(workspace) if workspace is not None else current.workspace,
                          current.created_at, now())
        return await self.writer.update_project(updated)


class CreateConversation:
    def __init__(self, projects: ProjectReader, writer: ConversationWriter): self.projects, self.writer = projects, writer
    async def execute(self, *, project_id: str, title: str = "New conversation") -> Conversation:
        if await self.projects.get_project(project_id) is None: raise ProjectNotFound(project_id)
        stamp = now()
        return await self.writer.create_conversation(Conversation(uuid4().hex, project_id, title.strip() or "New conversation", stamp, stamp))


class GetConversation:
    def __init__(self, reader: ConversationReader): self.reader = reader
    async def execute(self, conversation_id: str) -> Conversation:
        result = await self.reader.get_conversation(conversation_id)
        if result is None: raise ConversationNotFound(conversation_id)
        return result


class GetConversationHistory:
    def __init__(self, reader: ConversationReader): self.reader = reader
    async def execute(self, conversation_id: str) -> list[ConversationTurn]:
        return await self.reader.list_turns(conversation_id)


class SendConversationMessage:
    """Product orchestration; Runtime only receives ordinary AgentMessage history."""
    def __init__(self, conversations: ConversationReader & ConversationWriter, projects: ProjectReader, execute_agent):
        self.conversations, self.projects, self.execute_agent = conversations, projects, execute_agent

    async def execute(self, command: SendConversationMessageCommand) -> SendConversationMessageResult:
        prepared = await self._prepare(command)
        conversation, user_turn, history, project = prepared
        result = await self.execute_agent.execute(ExecuteAgentCommand(command.agent_key, command.message, conversation.conversation_id, command.user_id, history, {"working_directory": project.workspace, "project_id": project.project_id, "conversation_id": conversation.conversation_id}))
        return await self._finish(conversation, user_turn, result.run.output_text, result.run.run_id, command.message)

    async def _prepare(self, command: SendConversationMessageCommand):
        conversation = await GetConversation(self.conversations).execute(command.conversation_id)
        project = await self.projects.get_project(conversation.project_id)
        if project is None: raise ProjectNotFound(conversation.project_id)
        _workspace(project.workspace)
        message = command.message.strip()
        if not message: raise ValueError("Message is required")
        stamp = now()
        user_turn = await self.conversations.append_turn(ConversationTurn(uuid4().hex, conversation.conversation_id, "user", message, None, stamp))
        turns = await self.conversations.list_turns(conversation.conversation_id, limit=command.context_limit)
        history = tuple(AgentMessage(role=AgentRole(t.role), content=t.content) for t in turns[:-1] if t.role in ("user", "assistant"))
        return conversation, user_turn, history, project

    async def _finish(self, conversation, user_turn, content: str, run_id: str, message: str):
        assistant = await self.conversations.append_turn(ConversationTurn(uuid4().hex, conversation.conversation_id, "assistant", content, run_id, now()))
        if conversation.title == "New conversation":
            conversation = Conversation(conversation.conversation_id, conversation.project_id, message[:80], conversation.created_at, now(), conversation.archived_at)
            conversation = await self.conversations.update_conversation(conversation)
        return SendConversationMessageResult(conversation, user_turn, assistant)

    async def stream(self, command: SendConversationMessageCommand):
        conversation, user_turn, history, project = await self._prepare(command)
        text = ""
        run_id = ""
        async for update in self.execute_agent.stream(ExecuteAgentCommand(command.agent_key, command.message, conversation.conversation_id, command.user_id, history, {"working_directory": project.workspace, "project_id": project.project_id, "conversation_id": conversation.conversation_id})):
            run_id = update.run_id
            event = update.event
            if event.delta:
                text += event.delta
            if event.reply_text:
                text = event.reply_text
            yield update
            if event.event_type == "error":
                return
        if run_id and text:
            await self._finish(conversation, user_turn, text, run_id, command.message)
