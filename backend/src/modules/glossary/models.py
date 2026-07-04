from __future__ import annotations

from sqlalchemy import BigInteger, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from alkit_db.base import EntityBase


class GlossaryCategory(EntityBase):
    __tablename__ = "glossary_categories"

    name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(String(1024))


class GlossaryTerm(EntityBase):
    __tablename__ = "glossary_terms"
    __table_args__ = (
        UniqueConstraint("category_id", "term", name="uq_glossary_term"),
    )

    category_id: Mapped[int] = mapped_column(BigInteger, index=True)
    term: Mapped[str] = mapped_column(String(256))
    synonyms_json: Mapped[list | None] = mapped_column(JSONB)


class KnowledgeBaseGlossaryCategory(EntityBase):
    __tablename__ = "knowledge_base_glossary_categories"

    knowledge_base_id: Mapped[int] = mapped_column(BigInteger, index=True)
    category_id: Mapped[int] = mapped_column(BigInteger, index=True)

    __table_args__ = (
        UniqueConstraint("knowledge_base_id", "category_id", name="uq_kb_glossary_category"),
    )
