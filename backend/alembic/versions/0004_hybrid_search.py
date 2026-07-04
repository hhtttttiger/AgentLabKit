"""enable pg_trgm + GIN trigram index for hybrid search.

为 document_segments.content 列创建 pg_trgm GIN 索引，
支持中文/英文混合全文检索（trigram 匹配 + similarity 排序）。

Revision ID: 0004
Revises: 0003
"""
from __future__ import annotations

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 启用 pg_trgm 扩展（内置，无需额外安装）
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # 2. 在 content 列上创建 GIN trigram 索引
    #    支持 LIKE '%keyword%' 和 similarity() 查询
    #    CONCURRENTLY 不能在事务内执行，需设置 AUTOCOMMIT
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_document_segment_content_trgm "
            "ON document_segments USING gin (content gin_trgm_ops)"
        )


def downgrade() -> None:
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_document_segment_content_trgm")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
