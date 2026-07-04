"""ORM models for memory_records and memory_embeddings.

DESIGN NOTE: These ORM models exist SOLELY for Alembic metadata discovery
(auto-generation of migrations). Runtime data access is handled by
``packages/memory/src/memory/store.py`` using raw SQL via ``sqlalchemy.text()``
for full control over query structure and performance.

If you add a column to the raw SQL in store.py, you MUST also add the
corresponding ``Mapped`` column here for migrations to stay in sync.
Conversely, if Alembic auto-generates a migration from these models,
verify the new columns are handled in store.py's raw SQL.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from alkit_db.base import EntityBase

# pgvector — 延迟导入，单元测试环境可能没有安装
try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # pragma: no cover
    Vector = None  # type: ignore[assignment,misc]


class MemoryRecordOrm(EntityBase):
    """长期记忆记录。"""
    __tablename__ = "memory_records"

    user_id: Mapped[str] = mapped_column(String(128), index=True)
    session_id: Mapped[str | None] = mapped_column(String(128))
    memory_type: Mapped[str] = mapped_column(String(32), index=True)
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(String(1024))
    source_turn_ids_json: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    relevance_score: Mapped[float] = mapped_column(Float, default=0)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consolidated_from_json: Mapped[list[int]] = mapped_column(JSONB, default=list, server_default="[]")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_memory_records_user_type", "user_id", "memory_type"),
        Index("ix_memory_records_expires_at", "expires_at_utc"),
    )


class MemoryEmbeddingOrm(EntityBase):
    """记忆向量 embedding。"""
    __tablename__ = "memory_embeddings"

    memory_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    embedding_model: Mapped[str] = mapped_column(String(128), default="", server_default="")
    vector: Mapped[list | None] = mapped_column(Vector(1024), nullable=True)  # type: ignore[valid-type]
