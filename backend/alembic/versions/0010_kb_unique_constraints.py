"""kb: add unique constraints for UPSERT reliability

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-27

- segment_embeddings.segment_id: required so re-index UPSERT
  (pgvector_store.aupsert) can match on segment_id instead of the
  Snowflake PK id (which is never supplied in INSERT values).
- knowledge_document_recall_stats.document_id: required so recall-stats
  bulk UPSERT can atomically increment recall_count per document.
"""
from __future__ import annotations

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Dedup segment_embeddings: keep the row with the highest id per segment_id
    op.execute("""
        DELETE FROM public.segment_embeddings
        WHERE id NOT IN (
            SELECT MAX(id) FROM public.segment_embeddings
            GROUP BY segment_id
        )
    """)
    # Dedup recall_stats: keep the row with the highest recall_count per document_id
    op.execute("""
        DELETE FROM public.knowledge_document_recall_stats
        WHERE id NOT IN (
            SELECT id FROM (
                SELECT DISTINCT ON (document_id) id
                FROM public.knowledge_document_recall_stats
                ORDER BY document_id, recall_count DESC
            ) AS kept
        )
    """)
    op.execute(
        "ALTER TABLE public.segment_embeddings "
        "ADD CONSTRAINT uq_segment_embeddings_segment_id UNIQUE (segment_id)"
    )
    op.execute(
        "ALTER TABLE public.knowledge_document_recall_stats "
        "ADD CONSTRAINT uq_recall_stats_document_id UNIQUE (document_id)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE public.segment_embeddings "
        "DROP CONSTRAINT IF EXISTS uq_segment_embeddings_segment_id"
    )
    op.execute(
        "ALTER TABLE public.knowledge_document_recall_stats "
        "DROP CONSTRAINT IF EXISTS uq_recall_stats_document_id"
    )
