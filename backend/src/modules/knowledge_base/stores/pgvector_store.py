"""PgVectorStore — 基于 pgvector 的向量存储和检索，支持 pg_trgm 全文检索"""

from __future__ import annotations

from typing import Dict, List, Optional

from loguru import logger
from sqlalchemy import delete, func, select, case, literal
from sqlalchemy.dialects.postgresql import insert as pg_insert

from retrieval.stores.base import BaseVectorStore, VectorRecord, VectorSearchResult

from ..models import DocumentSegment, KnowledgeDocument, SegmentEmbedding


class PgVectorStore(BaseVectorStore):
    """使用 PostgreSQL + pgvector 实现向量存储

    collection 语义上对应一个 knowledge_base_id。
    通过 HNSW 索引实现高效近似最近邻检索。
    """

    def __init__(self, session_factory, dimensions: int = 1024):
        self._session_factory = session_factory
        self._dimensions = dimensions

    async def aupsert(self, collection: str, records: List[VectorRecord], session=None) -> None:
        """批量写入 / 更新向量记录

        collection → knowledge_base_id
        使用单条 INSERT ... VALUES (...), (...) + ON CONFLICT DO UPDATE，
        一次 round-trip 完成整批写入。

        Args:
            session: 可选的外部 AsyncSession。传入时复用该 session 的事务，
                     调用方负责 commit；未传入时自管 session 和 commit。
        """
        if not records:
            return

        kb_id = int(collection)
        values = [
            {
                "segment_id": int(r.id),
                "document_id": int(r.metadata.get("document_id", 0)),
                "knowledge_base_id": kb_id,
                "embedding_model": r.metadata.get("model", ""),
                "vector": r.vector,
            }
            for r in records
        ]

        async def _execute(s):
            stmt = pg_insert(SegmentEmbedding).values(values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["segment_id"],
                set_={
                    "vector": stmt.excluded.vector,
                    "embedding_model": stmt.excluded.embedding_model,
                },
            )
            await s.execute(stmt)

        if session is not None:
            await _execute(session)
        else:
            async with self._session_factory() as session:
                await _execute(session)
                await session.commit()

    async def aquery(
        self,
        collection: str,
        vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict] = None,
    ) -> List[VectorSearchResult]:
        """余弦相似度检索

        使用 pgvector 的 <=> 操作符（余弦距离），
        距离越小越相似，score = 1 - distance。
        """
        kb_id = int(collection)
        async with self._session_factory() as session:
            distance_expr = SegmentEmbedding.vector.cosine_distance(vector).label("distance")
            stmt = (
                select(SegmentEmbedding, distance_expr)
                .where(SegmentEmbedding.knowledge_base_id == kb_id)
                .order_by("distance")
                .limit(top_k)
            )

            # 额外过滤条件（如 document_id）
            if filters:
                if "document_id" in filters:
                    stmt = stmt.where(
                        SegmentEmbedding.document_id == int(filters["document_id"])
                    )

            results = (await session.execute(stmt)).all()
            return [
                VectorSearchResult(
                    id=str(row.SegmentEmbedding.segment_id),
                    score=round(1.0 - row.distance, 6),
                    metadata={
                        "document_id": str(row.SegmentEmbedding.document_id),
                        "knowledge_base_id": str(row.SegmentEmbedding.knowledge_base_id),
                        "embedding_model": row.SegmentEmbedding.embedding_model,
                    },
                )
                for row in results
            ]

    async def adelete(self, collection: str, ids: List[str]) -> None:
        """按 segment_id 删除向量记录"""
        kb_id = int(collection)
        int_ids = [int(i) for i in ids]
        async with self._session_factory() as session:
            stmt = (
                delete(SegmentEmbedding)
                .where(SegmentEmbedding.knowledge_base_id == kb_id)
                .where(SegmentEmbedding.segment_id.in_(int_ids))
            )
            await session.execute(stmt)
            await session.commit()

    async def adelete_by_document(self, collection: str, document_id: str) -> None:
        """按文档 ID 删除所有关联向量（幂等 re-index 用）"""
        kb_id = int(collection)
        doc_id = int(document_id)
        async with self._session_factory() as session:
            stmt = (
                delete(SegmentEmbedding)
                .where(SegmentEmbedding.knowledge_base_id == kb_id)
                .where(SegmentEmbedding.document_id == doc_id)
            )
            await session.execute(stmt)
            await session.commit()

    async def aquery_fulltext(
        self,
        collection: str,
        query_text: str,
        top_k: int = 10,
        filters: Optional[Dict] = None,
    ) -> List[VectorSearchResult]:
        """基于 pg_trgm 的全文检索

        查询 DocumentSegment.content（trigram GIN index），
        按 similarity + exact match 综合排序。
        """
        kb_id = int(collection)
        query = (query_text or "").strip()
        if not query:
            return []

        async with self._session_factory() as session:
            # 构建 similarity 表达式
            sim_score = func.similarity(DocumentSegment.content, query)

            # 短查询（<4字符）只用 LIKE，避免 trigram 噪音
            if len(query) < 4:
                score_expr = case(
                    (DocumentSegment.content.ilike(f"%{query}%"), literal(1.0)),
                    else_=literal(0.0),
                )
            else:
                score_expr = case(
                    (DocumentSegment.content.ilike(f"%{query}%"), literal(1.0)),
                    else_=sim_score * 0.4,
                )

            stmt = (
                select(
                    DocumentSegment.id,
                    DocumentSegment.content,
                    DocumentSegment.document_id,
                    score_expr.label("score"),
                )
                .join(KnowledgeDocument, DocumentSegment.document_id == KnowledgeDocument.id)
                .where(KnowledgeDocument.knowledge_base_id == kb_id)
                .where(score_expr > 0)
                .order_by(score_expr.desc())
                .limit(top_k)
            )

            if filters and "document_id" in filters:
                stmt = stmt.where(
                    DocumentSegment.document_id == int(filters["document_id"])
                )

            rows = (await session.execute(stmt)).all()

            return [
                VectorSearchResult(
                    id=str(row.id),
                    score=round(float(row.score), 6),
                    metadata={
                        "document_id": str(row.document_id),
                        "content_preview": row.content[:200] if row.content else "",
                    },
                )
                for row in rows
            ]
