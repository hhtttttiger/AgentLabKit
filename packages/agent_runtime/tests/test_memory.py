from __future__ import annotations

from datetime import UTC, datetime

import pytest



from agent_runtime import AgentMessage, AgentRole
from agent_runtime.memory import (
    ContextManager,
    ContextWindowConfig,
    GatewaySummarizer,
    InMemorySessionStore,
    MEMORY_KIND_METADATA_KEY,
    MEMORY_KIND_SUMMARY,
    MessagePriority,
    SessionSnapshot,
    mark_message_priority,
    resolve_message_priority,
)
from llm_gateway import ProviderId, TextGenerateResponse


class CharacterTokenCounter:
    def count(self, text: str) -> int:
        return len(text)

    def count_messages(self, messages: list[AgentMessage]) -> int:
        total = 0
        for message in messages:
            total += 4 + len(message.content)
            if message.name:
                total += len(message.name)
        return total


class RecordingSummarizer:
    def __init__(self, summary_text: str = "compressed summary") -> None:
        self.summary_text = summary_text
        self.calls: list[list[AgentMessage]] = []

    async def summarize(
        self,
        messages: list[AgentMessage],
        context_hint: str | None = None,
    ) -> str:
        self.calls.append(list(messages))
        return self.summary_text


class FailingSummarizer:
    async def summarize(
        self,
        messages: list[AgentMessage],
        context_hint: str | None = None,
    ) -> str:
        raise RuntimeError("summary failed")


class FakeGateway:
    def __init__(self, responses: list[TextGenerateResponse]) -> None:
        self.responses = list(responses)
        self.requests = []

    async def generate_text(self, request):
        self.requests.append(request)
        return self.responses.pop(0)


def _message(role: AgentRole, content: str) -> AgentMessage:
    return AgentMessage(role=role, content=content)


class TestMessagePriority:
    def test_resolve_message_priority_defaults_to_normal(self):
        message = AgentMessage(role=AgentRole.USER, content="hello")
        assert resolve_message_priority(message) is MessagePriority.NORMAL

    def test_mark_message_priority_sets_metadata(self):
        message = mark_message_priority(
            AgentMessage(role=AgentRole.ASSISTANT, content="important"),
            MessagePriority.PINNED,
        )
        assert message.metadata["_priority"] == "pinned"
        assert resolve_message_priority(message) is MessagePriority.PINNED


@pytest.mark.asyncio
class TestContextManager:
    async def test_prepare_context_keeps_history_when_budget_allows(self):
        manager = ContextManager(
            ContextWindowConfig(
                max_total_tokens=200,
                reserve_for_response=0,
                reserve_for_system=0,
                min_recent_messages=2,
                enable_summarization=False,
            ),
            token_counter=CharacterTokenCounter(),
        )
        history = [
            _message(AgentRole.USER, "order"),
            _message(AgentRole.ASSISTANT, "status"),
            _message(AgentRole.USER, "tracking"),
        ]

        window = await manager.prepare_context(
            system_prompt="support",
            history=history,
            user_message="where is it",
        )

        assert window.summary is None
        assert window.dropped_count == 0
        assert [message.content for message in window.to_messages()] == [
            "order",
            "status",
            "tracking",
        ]

    async def test_prepare_context_preserves_pinned_messages(self):
        manager = ContextManager(
            ContextWindowConfig(
                max_total_tokens=30,
                reserve_for_response=0,
                reserve_for_system=0,
                min_recent_messages=1,
                enable_summarization=False,
            ),
            token_counter=CharacterTokenCounter(),
        )
        history = [
            _message(AgentRole.USER, "discard-me"),
            mark_message_priority(
                _message(AgentRole.ASSISTANT, "pin"),
                MessagePriority.PINNED,
            ),
            _message(AgentRole.USER, "keep-recent"),
        ]

        window = await manager.prepare_context(
            system_prompt="s",
            history=history,
            user_message="u",
        )

        kept = [message.content for message in window.to_messages()]
        assert "pin" in kept
        assert "keep-recent" in kept
        assert "discard-me" not in kept
        assert window.dropped_count == 1

    async def test_prepare_context_summarizes_omitted_messages(self):
        summarizer = RecordingSummarizer("summary v2")
        manager = ContextManager(
            ContextWindowConfig(
                max_total_tokens=30,
                reserve_for_response=0,
                reserve_for_system=0,
                summarize_threshold_ratio=0.1,
                min_recent_messages=1,
                enable_summarization=True,
            ),
            token_counter=CharacterTokenCounter(),
            summarizer=summarizer,
        )
        history = [
            AgentMessage(
                role=AgentRole.SYSTEM,
                content="summary v1",
                metadata={MEMORY_KIND_METADATA_KEY: MEMORY_KIND_SUMMARY},
            ),
            _message(AgentRole.USER, "alpha"),
            _message(AgentRole.ASSISTANT, "beta"),
            _message(AgentRole.USER, "gamma"),
        ]

        window = await manager.prepare_context(
            system_prompt="s",
            history=history,
            user_message="u",
        )

        assert window.summary is not None
        assert window.summary.content == "summary v2"
        assert window.summary.metadata[MEMORY_KIND_METADATA_KEY] == MEMORY_KIND_SUMMARY
        assert window.summarized_count == 2
        assert window.dropped_count == 0
        assert [message.content for message in summarizer.calls[0]] == [
            "summary v1",
            "alpha",
            "beta",
        ]

    async def test_prepare_context_falls_back_when_summary_fails(self):
        manager = ContextManager(
            ContextWindowConfig(
                max_total_tokens=22,
                reserve_for_response=0,
                reserve_for_system=0,
                summarize_threshold_ratio=0.1,
                min_recent_messages=1,
                enable_summarization=True,
            ),
            token_counter=CharacterTokenCounter(),
            summarizer=FailingSummarizer(),
        )

        window = await manager.prepare_context(
            system_prompt="s",
            history=[
                _message(AgentRole.USER, "alpha"),
                _message(AgentRole.ASSISTANT, "beta"),
                _message(AgentRole.USER, "gamma"),
            ],
            user_message="u",
        )

        assert window.summary is None
        assert window.dropped_count == 1


@pytest.mark.asyncio
class TestGatewaySummarizer:
    async def test_gateway_summarizer_builds_prompt_and_returns_text(self):
        gateway = FakeGateway(
            [
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text="short summary",
                )
            ]
        )
        summarizer = GatewaySummarizer(gateway, model="summary-model")

        result = await summarizer.summarize(
            [
                _message(AgentRole.USER, "Need refund"),
                _message(AgentRole.ASSISTANT, "Refund approved"),
            ],
            context_hint="support escalation",
        )

        assert result == "short summary"
        assert gateway.requests[0].model == "summary-model"
        assert "support escalation" in gateway.requests[0].prompt
        assert "[user] Need refund" in gateway.requests[0].prompt

    async def test_gateway_summarizer_returns_empty_for_empty_messages(self):
        gateway = FakeGateway([])
        summarizer = GatewaySummarizer(gateway)

        result = await summarizer.summarize([])

        assert result == ""
        assert gateway.requests == []


@pytest.mark.asyncio
class TestInMemorySessionStore:
    async def test_save_load_and_delete_snapshot(self):
        store = InMemorySessionStore()
        snapshot = SessionSnapshot(
            session_id="session-1",
            messages=[_message(AgentRole.USER, "hello")],
            summary="summary",
            turn_count=2,
            total_tokens_consumed=42,
            updated_at=datetime.now(UTC),
        )

        await store.save("session-1", snapshot)
        loaded = await store.load("session-1")

        assert loaded is not None
        assert loaded.session_id == "session-1"
        assert loaded.summary == "summary"
        assert loaded.turn_count == 2
        assert loaded.total_tokens_consumed == 42

        await store.delete("session-1")
        assert await store.load("session-1") is None
