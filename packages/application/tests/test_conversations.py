from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from agent_runtime import AgentTurnStreamEvent

from application.conversations import (
    ConversationNotFound,
    ProjectNotFound,
    CreateConversation,
    CreateProject,
    GetConversationHistory,
    SendConversationMessage,
    SendConversationMessageCommand,
    UpdateProject,
    Project, Conversation, ConversationTurn,
)
from application.execution.execute_agent import ExecuteAgent
from application.execution.contracts import ExecuteAgentCommand


class MemoryStore:
    def __init__(self):
        self.projects = {}
        self.conversations = {}
        self.turns = {}

    async def get_project(self, project_id): return self.projects.get(project_id)
    async def list_projects(self): return list(self.projects.values())
    async def create_project(self, project): self.projects[project.project_id] = project; return project
    async def update_project(self, project): self.projects[project.project_id] = project; return project
    async def get_conversation(self, conversation_id): return self.conversations.get(conversation_id)
    async def list_project_conversations(self, project_id): return [c for c in self.conversations.values() if c.project_id == project_id]
    async def list_turns(self, conversation_id, *, limit=None):
        values = self.turns.get(conversation_id, [])
        return values[-limit:] if limit is not None else values
    async def create_conversation(self, conversation): self.conversations[conversation.conversation_id] = conversation; return conversation
    async def update_conversation(self, conversation): self.conversations[conversation.conversation_id] = conversation; return conversation
    async def append_turn(self, turn): self.turns.setdefault(turn.conversation_id, []).append(turn); return turn


class FakeAgent:
    def __init__(self, replies: list[str] | None = None, *, fail_stream=False):
        self.replies = replies or ["first", "second"]
        self.calls = []
        self.fail_stream = fail_stream

    async def execute(self, command):
        self.calls.append(command)
        reply = self.replies[len(self.calls) - 1]
        return SimpleNamespace(run=SimpleNamespace(output_text=reply, run_id=f"run-{len(self.calls)}"))

    def stream(self, command):
        async def updates():
            self.calls.append(command)
            if self.fail_stream:
                raise RuntimeError("provider unavailable")
            yield SimpleNamespace(run_id="run-stream", event=AgentTurnStreamEvent(event_type="reply_delta", session_id="c", trace_id="t", delta="streamed"))
            yield SimpleNamespace(run_id="run-stream", event=AgentTurnStreamEvent(event_type="reply_completed", session_id="c", trace_id="t", reply_text="streamed"))
        return updates()


class DisconnectingAgent:
    def __init__(self):
        self.closed = False

    def stream(self, command):
        async def updates():
            try:
                yield SimpleNamespace(run_id="run-disconnected", event=AgentTurnStreamEvent(event_type="reply_delta", session_id="c", trace_id="t", delta="partial"))
                await asyncio.Event().wait()
            finally:
                self.closed = True
        return updates()


@pytest.mark.asyncio
async def test_execute_agent_closes_executor_stream_on_disconnect():
    class Reader:
        async def resolve(self, agent_key): return SimpleNamespace(agent_key=agent_key, agent_version="1")

    class Executor:
        def __init__(self): self.closed = False
        def stream(self, **kwargs):
            async def updates():
                try:
                    yield SimpleNamespace()
                    await asyncio.Event().wait()
                finally:
                    self.closed = True
            return updates()

    executor = Executor()
    stream = ExecuteAgent(executor, Reader()).stream(ExecuteAgentCommand("local-agent", "hello"))
    await stream.__anext__()
    await stream.aclose()
    assert executor.closed is True


@pytest.mark.asyncio
async def test_multi_turn_context_and_run_linkage(tmp_path: Path):
    store = MemoryStore()
    project = await CreateProject(store).execute(name="AgentLabKit", workspace=str(tmp_path))
    conversation = await CreateConversation(store, store).execute(project_id=project.project_id)
    agent = FakeAgent()
    use_case = SendConversationMessage(store, store, agent)

    await use_case.execute(SendConversationMessageCommand(conversation.conversation_id, "choose option two"))
    result = await use_case.execute(SendConversationMessageCommand(conversation.conversation_id, "continue with that"))

    assert [m.content for m in agent.calls[1].history] == ["choose option two", "first"]
    assert result.assistant_turn.run_id == "run-2"
    assert result.conversation.title == "choose option two"


@pytest.mark.asyncio
async def test_stream_persists_assistant_only_after_success(tmp_path: Path):
    store = MemoryStore()
    project = await CreateProject(store).execute(name="P", workspace=str(tmp_path))
    conversation = await CreateConversation(store, store).execute(project_id=project.project_id)

    events = [item async for item in SendConversationMessage(store, store, FakeAgent()).stream(SendConversationMessageCommand(conversation.conversation_id, "hello"))]
    turns = await store.list_turns(conversation.conversation_id)
    assert len(events) == 2
    assert [(turn.role, turn.run_id) for turn in turns] == [("user", None), ("assistant", "run-stream")]

    failed = await CreateConversation(store, store).execute(project_id=project.project_id)
    with pytest.raises(RuntimeError):
        [item async for item in SendConversationMessage(store, store, FakeAgent(fail_stream=True)).stream(SendConversationMessageCommand(failed.conversation_id, "retry me"))]
    assert [(turn.role, turn.run_id) for turn in await store.list_turns(failed.conversation_id)] == [("user", None)]


@pytest.mark.asyncio
async def test_client_disconnect_closes_runtime_stream_without_fake_assistant(tmp_path: Path):
    store = MemoryStore()
    project = await CreateProject(store).execute(name="P", workspace=str(tmp_path))
    conversation = await CreateConversation(store, store).execute(project_id=project.project_id)
    agent = DisconnectingAgent()
    stream = SendConversationMessage(store, store, agent).stream(SendConversationMessageCommand(conversation.conversation_id, "disconnect me"))

    await stream.__anext__()
    assert [(turn.role, turn.run_id) for turn in await store.list_turns(conversation.conversation_id)] == [("user", None)]
    await stream.aclose()

    assert agent.closed is True
    assert [(turn.role, turn.run_id) for turn in await store.list_turns(conversation.conversation_id)] == [("user", None)]


@pytest.mark.asyncio
async def test_restart_persistence_and_history_not_found(tmp_path: Path):
    store = MemoryStore()
    project = await CreateProject(store).execute(name="P", workspace=str(tmp_path))
    conversation = await CreateConversation(store, store).execute(project_id=project.project_id)
    await store.append_turn(SimpleNamespace(turn_id="turn", conversation_id=conversation.conversation_id, role="user", content="persist", run_id=None, created_at=project.created_at))
    # The SQLite restart invariant is covered by the Desktop adapter tests;
    # this test focuses on the application not-found contract.
    assert (await store.get_project(project.project_id)).name == "P"
    assert (await GetConversationHistory(store).execute(conversation.conversation_id))[0].content == "persist"
    with pytest.raises(ConversationNotFound):
        await GetConversationHistory(store).execute("missing")


@pytest.mark.asyncio
async def test_project_patch_validation(tmp_path: Path):
    store = MemoryStore()
    project = await CreateProject(store).execute(name="P", workspace=str(tmp_path))
    with pytest.raises(ValueError):
        await UpdateProject(store, store).execute(project.project_id, name="   ")
    with pytest.raises(ProjectNotFound):
        await UpdateProject(store, store).execute("missing", name="Q")
