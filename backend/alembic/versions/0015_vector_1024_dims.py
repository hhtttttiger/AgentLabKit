"""change pgvector columns from 1536 to 1024 dimensions for Zhipu embedding-3.

Alter segment_embeddings.vector and memory_embeddings.vector columns,
rebuild HNSW index on segment_embeddings.

Revision ID: 0015
Revises: 0014
"""
from __future__ import annotations

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Drop HNSW index before altering column type
    op.execute("DROP INDEX IF EXISTS ix_seg_emb_kb_vec")
    op.execute("DROP INDEX IF EXISTS ix_memory_embeddings_vec")

    # 2. Alter vector columns to 1024 dimensions
    op.execute(
        "ALTER TABLE segment_embeddings ALTER COLUMN vector TYPE public.vector(1024)"
    )
    op.execute(
        "ALTER TABLE memory_embeddings ALTER COLUMN vector TYPE public.vector(1024)"
    )

    # 3. Rebuild HNSW indexes
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_seg_emb_kb_vec "
        "ON segment_embeddings USING hnsw (vector public.vector_cosine_ops) "
        "WITH (m='16', ef_construction='64')"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_memory_embeddings_vec "
        "ON memory_embeddings USING hnsw (vector public.vector_cosine_ops)"
    )


def downgrade() -> None:
    # 1. Drop HNSW indexes
    op.execute("DROP INDEX IF EXISTS ix_seg_emb_kb_vec")
    op.execute("DROP INDEX IF EXISTS ix_memory_embeddings_vec")

    # 2. Alter vector columns back to 1536
    op.execute(
        "ALTER TABLE segment_embeddings ALTER COLUMN vector TYPE public.vector(1536)"
    )
    op.execute(
        "ALTER TABLE memory_embeddings ALTER COLUMN vector TYPE public.vector(1536)"
    )

    # 3. Rebuild HNSW indexes
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_seg_emb_kb_vec "
        "ON segment_embeddings USING hnsw (vector public.vector_cosine_ops) "
        "WITH (m='16', ef_construction='64')"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_memory_embeddings_vec "
        "ON memory_embeddings USING hnsw (vector public.vector_cosine_ops)"
    )
