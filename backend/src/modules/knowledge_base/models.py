from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from alkit_db.base import EntityBase

# pgvector — 延迟导入，单元测试环境可能没有安装
try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # pragma: no cover
    Vector = None  # type: ignore[assignment,misc]


# ── Enums ──────────────────────────────────────────────────────────


class KbStatus(str, Enum):
    ACTIVE = "active"
    PROCESSING = "processing"
    DISABLED = "disabled"
    DELETED = "deleted"


class IngestStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentSourceType(str, Enum):
    FILE = "file"
    QA = "qa"


# ── Models ─────────────────────────────────────────────────────────


class KnowledgeBaseEntity(EntityBase):
    __tablename__ = "knowledge_bases"

    name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(String(1024))
    icon: Mapped[str | None] = mapped_column(String(64))
    index_names_json: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    config_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    status: Mapped[str] = mapped_column(String(32), default=KbStatus.ACTIVE, server_default="active")


class KnowledgeFolder(EntityBase):
    __tablename__ = "knowledge_folders"

    knowledge_base_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), index=True,
    )
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("knowledge_folders.id", ondelete="SET NULL"), index=True,
    )
    name: Mapped[str] = mapped_column(String(256))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class KnowledgeDocument(EntityBase):
    __tablename__ = "knowledge_documents"

    knowledge_base_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), index=True,
    )
    folder_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("knowledge_folders.id", ondelete="SET NULL"), index=True,
    )
    title: Mapped[str] = mapped_column(String(512))
    source_type: Mapped[str] = mapped_column(String(32))
    source_uri: Mapped[str | None] = mapped_column(String(1024))
    content_type: Mapped[str | None] = mapped_column(String(128))
    content: Mapped[str | None] = mapped_column(Text)
    qa_question: Mapped[str | None] = mapped_column(Text)
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)
    stored_file_id: Mapped[str | None] = mapped_column(String(256))
    ingest_error: Mapped[str | None] = mapped_column(Text)
    ingested_at_utc: Mapped[datetime | None] = mapped_column(DateTime)
    extra_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    status: Mapped[str] = mapped_column(String(32), default=IngestStatus.PENDING)
    segment_count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("ix_knowledge_doc_kb_status", "knowledge_base_id", "status"),
    )


class KnowledgeDocumentRecallStat(EntityBase):
    __tablename__ = "knowledge_document_recall_stats"

    document_id: Mapped[int] = mapped_column(BigInteger, index=True)
    recall_count: Mapped[int] = mapped_column(Integer, default=0)
    last_recalled_at_utc: Mapped[datetime | None] = mapped_column(DateTime)

    __table_args__ = (
        UniqueConstraint("document_id", name="uq_recall_stats_document_id"),
    )


class DocumentSegment(EntityBase):
    __tablename__ = "document_segments"

    document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True,
    )
    segment_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    extra_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    __table_args__ = (
        Index("ix_document_segment_doc_idx", "document_id", "segment_index"),
    )


class DocumentProcessingJob(EntityBase):
    __tablename__ = "document_processing_jobs"

    document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True,
    )
    job_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default=JobStatus.PENDING)
    current_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stage_progress_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at_utc: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at_utc: Mapped[datetime | None] = mapped_column(DateTime)


class DocumentIndex(EntityBase):
    __tablename__ = "document_indexes"

    knowledge_base_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), index=True,
    )
    document_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True,
    )
    index_name: Mapped[str] = mapped_column(String(128))
    index_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    config_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    stats_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    built_at_utc: Mapped[datetime | None] = mapped_column(DateTime)


class SegmentEmbedding(EntityBase):
    """分段向量 — 使用 pgvector 存储和检索 embedding"""
    __tablename__ = "segment_embeddings"

    segment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("document_segments.id", ondelete="CASCADE"),
        index=True,
    )
    document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True,
    )
    knowledge_base_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), index=True,
    )
    embedding_model: Mapped[str] = mapped_column(String(128))
    vector: Mapped[list] = mapped_column(Vector(1024))  # type: ignore[valid-type]

    __table_args__ = (
        UniqueConstraint("segment_id", name="uq_segment_embeddings_segment_id"),
        Index(
            "ix_seg_emb_kb_vec",
            "vector",
            postgresql_using="hnsw",
            postgresql_ops={"vector": "vector_cosine_ops"},
            postgresql_with={"m": 16, "ef_construction": 64},
        ),
    )
