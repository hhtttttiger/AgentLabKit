from pathlib import Path

import pytest

from application.conversations import CreateConversation, CreateProject
from desktop.local.composition import ConversationMessageBody
from desktop.local.store import LocalConversationStore, LocalDatabase


@pytest.mark.asyncio
async def test_project_conversation_turns_survive_database_restart(tmp_path: Path):
    path = tmp_path / "agentlab.db"
    db = LocalDatabase(path)
    store = LocalConversationStore(db)
    project = await CreateProject(store).execute(name="AgentLabKit", workspace=str(tmp_path))
    conversation = await CreateConversation(store, store).execute(project_id=project.project_id)
    await store.append_turn(type("Turn", (), {"turn_id": "t1", "conversation_id": conversation.conversation_id, "role": "user", "content": "hello", "run_id": None, "created_at": project.created_at})())
    db.close()

    db = LocalDatabase(path)
    store = LocalConversationStore(db)
    assert (await store.get_project(project.project_id)).workspace == str(tmp_path.resolve())
    turns = await store.list_turns(conversation.conversation_id)
    assert [(turn.role, turn.content, turn.run_id) for turn in turns] == [("user", "hello", None)]
    db.close()


def test_conversation_message_contract_does_not_accept_arbitrary_agent():
    assert "agentKey" not in ConversationMessageBody.model_fields
