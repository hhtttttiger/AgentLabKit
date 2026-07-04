from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import text

from alkit_db.base import EntityBase


class ChatSessionOrm(EntityBase):
    __tablename__ = "chat_sessions"

    user_id: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(String(512))
    model_type: Mapped[str] = mapped_column(String(16))
    model_id: Mapped[str] = mapped_column(String(128))
    message_count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index(
            "ix_chat_sessions_user_updated",
            "user_id",
            text("updated_at_utc DESC"),
        ),
    )


class ChatMessageOrm(EntityBase):
    __tablename__ = "chat_messages"

    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="sent")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    trace_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_chat_messages_session_created", "session_id", "created_at_utc"),
    )
