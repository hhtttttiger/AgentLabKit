"""Session management — load, restore, save session snapshots.

Extracted from ``engine.py`` to isolate session persistence logic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..contracts.models import AgentMessage, AgentRole, AgentTurnResult, AgentTurnRequest
from ..memory import (
    InMemorySessionStore,
    MEMORY_KIND_METADATA_KEY,
    MEMORY_KIND_SUMMARY,
    SessionSnapshot,
    SessionStore,
    is_summary_message,
)

if TYPE_CHECKING:
    from ..config import AgentSettings
    from ..memory import ContextWindow


class SessionManager:
    """Stateless helper for session operations — methods extracted from ``AgentRuntime``."""

    def __init__(self, session_store: SessionStore | None = None) -> None:
        self.session_store = session_store

    async def load_session_snapshot(
        self,
        request: AgentTurnRequest,
        settings: AgentSettings,
    ) -> SessionSnapshot | None:
        if (
            not settings.memory.enabled
            or not settings.memory.persist_sessions
            or self.session_store is None
            or request.history
        ):
            return None
        return await self.session_store.load(request.session_id)

    @staticmethod
    def restore_request_history(
        request: AgentTurnRequest,
        snapshot: SessionSnapshot | None,
    ) -> AgentTurnRequest:
        if snapshot is None:
            return request
        restored_history = [message.model_copy(deep=True) for message in snapshot.messages]
        if snapshot.summary and not any(
            is_summary_message(message) for message in restored_history
        ):
            restored_history.insert(
                0,
                AgentMessage(
                    role=AgentRole.SYSTEM,
                    content=snapshot.summary,
                    metadata={MEMORY_KIND_METADATA_KEY: MEMORY_KIND_SUMMARY},
                ),
            )
        return request.model_copy(update={"history": restored_history})

    async def save_session_snapshot(
        self,
        *,
        request: AgentTurnRequest,
        result: AgentTurnResult,
        snapshot: SessionSnapshot | None,
        settings: AgentSettings,
    ) -> None:
        if (
            not settings.memory.enabled
            or not settings.memory.persist_sessions
            or self.session_store is None
        ):
            return
        persisted_messages = [message.model_copy(deep=True) for message in request.history]
        persisted_messages.extend(
            SessionManager._normalize_persisted_turn_messages(request, result)
        )
        summary_text = SessionManager._extract_summary_text(persisted_messages)
        total_tokens = snapshot.total_tokens_consumed if snapshot is not None else 0
        total_tokens += (result.usage.total_tokens or 0) if result.usage is not None else 0
        turn_count = (snapshot.turn_count if snapshot is not None else 0) + 1
        await self.session_store.save(
            request.session_id,
            SessionSnapshot(
                session_id=request.session_id,
                messages=persisted_messages,
                summary=summary_text,
                turn_count=turn_count,
                total_tokens_consumed=total_tokens,
            ),
        )

    async def best_effort_save_on_error(
        self,
        *,
        request: AgentTurnRequest,
        snapshot: SessionSnapshot | None,
        settings: AgentSettings,
    ) -> None:
        """Attempt to persist current history on error so the turn is not lost."""
        if (
            not settings.memory.enabled
            or not settings.memory.persist_sessions
            or self.session_store is None
        ):
            return
        try:
            persisted_messages = [message.model_copy(deep=True) for message in request.history]
            persisted_messages.append(
                AgentMessage(role=AgentRole.USER, content=request.user_message),
            )
            summary_text = self._extract_summary_text(persisted_messages)
            turn_count = (snapshot.turn_count if snapshot is not None else 0) + 1
            total_tokens = snapshot.total_tokens_consumed if snapshot is not None else 0
            await self.session_store.save(
                request.session_id,
                SessionSnapshot(
                    session_id=request.session_id,
                    messages=persisted_messages,
                    summary=summary_text,
                    turn_count=turn_count,
                    total_tokens_consumed=total_tokens,
                ),
            )
        except Exception:
            pass

    @staticmethod
    def _extract_summary_text(history: list[AgentMessage]) -> str | None:
        for message in history:
            if is_summary_message(message):
                return message.content
        return None

    @staticmethod
    def _normalize_persisted_turn_messages(
        request: AgentTurnRequest,
        result: AgentTurnResult,
    ) -> list[AgentMessage]:
        normalized = [message.model_copy(deep=True) for message in result.raw_messages]
        has_user = any(message.role is AgentRole.USER for message in normalized)
        has_assistant = any(message.role is AgentRole.ASSISTANT for message in normalized)
        if not has_user:
            normalized.insert(0, AgentMessage(role=AgentRole.USER, content=request.user_message))
        if result.reply_text and not has_assistant:
            normalized.append(AgentMessage(role=AgentRole.ASSISTANT, content=result.reply_text))
        return normalized

    @staticmethod
    def trim_history(
        history: list[AgentMessage],
        settings: AgentSettings,
    ) -> list[AgentMessage]:
        if settings.max_history_messages <= 0:
            return []
        return list(history[-settings.max_history_messages :])


__all__ = ["SessionManager"]
