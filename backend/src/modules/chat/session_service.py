from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from alkit_db.engine import get_session_factory
from common.errors import NotFoundError

from .models import ChatMessageOrm, ChatSessionOrm
from .schemas import (
    CreateSessionRequest,
    SaveTurnRequest,
    SaveTurnResponse,
    UpdateSessionRequest,
)

logger = logging.getLogger(__name__)


class ChatSessionService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None):
        self._session_factory = session_factory or get_session_factory()

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    async def list_sessions(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ChatSessionOrm], int]:
        async with self._session_factory() as session:
            base = select(ChatSessionOrm).where(ChatSessionOrm.user_id == user_id)
            count_q = (
                select(func.count())
                .select_from(ChatSessionOrm)
                .where(ChatSessionOrm.user_id == user_id)
            )
            total = (await session.execute(count_q)).scalar() or 0

            items = (
                await session.execute(
                    base.order_by(ChatSessionOrm.updated_at_utc.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size),
                )
            ).scalars().all()

            return list(items), total

    async def create_session(
        self,
        user_id: str,
        data: CreateSessionRequest,
    ) -> ChatSessionOrm:
        async with self._session_factory() as session:
            obj = ChatSessionOrm(
                user_id=user_id,
                title=data.title,
                model_type=data.model_type,
                model_id=data.model_id,
            )
            session.add(obj)
            await session.commit()
            await session.refresh(obj)
            return obj

    async def get_session(
        self,
        session_id: int,
        user_id: str,
    ) -> ChatSessionOrm:
        async with self._session_factory() as session:
            obj = await session.get(ChatSessionOrm, session_id)
            if obj is None:
                raise NotFoundError("ChatSession", str(session_id))
            if obj.user_id != user_id:
                raise NotFoundError("ChatSession", str(session_id))
            return obj

    async def update_session(
        self,
        session_id: int,
        user_id: str,
        data: UpdateSessionRequest,
    ) -> ChatSessionOrm:
        async with self._session_factory() as session:
            obj = await session.get(ChatSessionOrm, session_id)
            if obj is None or obj.user_id != user_id:
                raise NotFoundError("ChatSession", str(session_id))

            update_data = data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(obj, key, value)

            await session.commit()
            await session.refresh(obj)
            return obj

    async def delete_session(
        self,
        session_id: int,
        user_id: str,
    ) -> None:
        async with self._session_factory() as session:
            obj = await session.get(ChatSessionOrm, session_id)
            if obj is None or obj.user_id != user_id:
                raise NotFoundError("ChatSession", str(session_id))
            await session.delete(obj)
            await session.commit()

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    async def list_messages(
        self,
        session_id: int,
        user_id: str,
        cursor: int | None = None,
        limit: int = 50,
    ) -> tuple[list[ChatMessageOrm], bool]:
        async with self._session_factory() as session:
            # Ownership check
            sess = await session.get(ChatSessionOrm, session_id)
            if sess is None or sess.user_id != user_id:
                raise NotFoundError("ChatSession", str(session_id))

            base = select(ChatMessageOrm).where(
                ChatMessageOrm.session_id == session_id,
            )
            if cursor is not None:
                base = base.where(ChatMessageOrm.id > cursor)

            rows = (
                await session.execute(
                    base.order_by(ChatMessageOrm.id.asc()).limit(limit + 1),
                )
            ).scalars().all()

            has_more = len(rows) > limit
            messages = rows[:limit]
            return list(messages), has_more

    async def save_turn(
        self,
        session_id: int,
        user_id: str,
        data: SaveTurnRequest,
    ) -> SaveTurnResponse:
        async with self._session_factory() as session:
            # Ownership check
            sess = await session.get(ChatSessionOrm, session_id)
            if sess is None or sess.user_id != user_id:
                raise NotFoundError("ChatSession", str(session_id))

            user_msg = ChatMessageOrm(
                session_id=session_id,
                role=data.user_message.role,
                content=data.user_message.content,
                status=data.user_message.status,
                error_message=data.user_message.error_message,
                trace_json=data.user_message.trace_json,
            )
            assistant_msg = ChatMessageOrm(
                session_id=session_id,
                role=data.assistant_message.role,
                content=data.assistant_message.content,
                status=data.assistant_message.status,
                error_message=data.assistant_message.error_message,
                trace_json=data.assistant_message.trace_json,
            )
            session.add_all([user_msg, assistant_msg])

            # Increment message count
            sess.message_count = (sess.message_count or 0) + 2

            await session.commit()
            await session.refresh(user_msg)
            await session.refresh(assistant_msg)

            return SaveTurnResponse(
                user_message_id=user_msg.id,
                assistant_message_id=assistant_msg.id,
            )
