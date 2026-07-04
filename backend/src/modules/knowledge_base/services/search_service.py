"""SearchService — 搜索操作（极薄适配层）。

所有 RAG 搜索逻辑委托给 retrieval_service，
本服务只负责：映射结果 schema + 更新 recall stats。
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import NotFoundError
from ..models import (
    DocumentSegment,
    KnowledgeDocument,
    KnowledgeDocumentRecallStat,
    KnowledgeBaseEntity,
)
from ..schemas import (
    SearchRequest,
    KbSearchResponse,
    KbSearchResult,
)


class SearchService:

    def __init__(self, db: AsyncSession, retrieval_service=None):
        self._db = db
        self._retrieval = retrieval_service

    async def search(self, kb_id: int, req: SearchRequest) -> KbSearchResponse:
        """在知识库中搜索 — 委托 retrieval_service。"""
        # 校验知识库存在
        kb = await self._db.get(KnowledgeBaseEntity, kb_id)
        if kb is None:
            raise NotFoundError("KnowledgeBase", str(kb_id))

        if self._retrieval is None:
            # 降级：SQL LIKE 搜索
            return await self._fallback_search(kb_id, req)

        # 委托 retrieval service 执行搜索（支持 vector/fulltext/hybrid）
        # document_id 和 document_type 现在由 retrieval_service 写入 SearchResult.metadata
        results = await self._retrieval.asearch(
            str(kb_id), req.query, top_k=req.top_k, search_mode=req.search_mode
        )

        # 组装结果 — 从 retrieval_service 返回的 metadata 中读取文档信息
        search_results = []
        recalled_doc_ids: set[int] = set()
        for r in results:
            doc_id_str = r.metadata.get("document_id", "")
            doc_name = r.source
            doc_type = r.metadata.get("document_type", "")

            vector_score = r.metadata.get("vector_score", r.score) if r.metadata else r.score
            fulltext_score = r.metadata.get("fulltext_score", 0.0) if r.metadata else 0.0
            # 清理 metadata 中的内部字段，不暴露给前端
            clean_metadata = {
                k: v for k, v in (r.metadata or {}).items()
                if k not in ("vector_score", "fulltext_score", "document_id", "document_type")
            }
            search_results.append(KbSearchResult(
                segment_id=r.id,
                document_id=doc_id_str,
                content=r.text,
                score=r.score,
                metadata_json=json.dumps(clean_metadata) if clean_metadata else None,
                vector_score=vector_score,
                fulltext_score=fulltext_score,
                document_name=doc_name,
                document_type=doc_type,
            ))
            if doc_id_str:
                recalled_doc_ids.add(int(doc_id_str))

        # 异步 fire-and-forget 更新召回统计，不阻塞搜索响应
        if recalled_doc_ids:
            asyncio.create_task(self._increment_recall_stats_async(list(recalled_doc_ids)))

        return KbSearchResponse(results=search_results)

    # ── Internal ───────────────────────────────────────────────────

    async def _fallback_search(self, kb_id: int, req: SearchRequest) -> KbSearchResponse:
        """retrieval 未启用时的降级搜索 — pg_trgm similarity + ILIKE。"""
        from sqlalchemy import func, case, literal

        query = req.query.strip()
        if not query:
            return KbSearchResponse(results=[])

        # 短查询用 ILIKE，长查询加 similarity 排序
        if len(query) < 4:
            score_expr = case(
                (DocumentSegment.content.ilike(f"%{query}%"), literal(1.0)),
                else_=literal(0.0),
            )
        else:
            sim_score = func.similarity(DocumentSegment.content, query)
            score_expr = case(
                (DocumentSegment.content.ilike(f"%{query}%"), literal(1.0)),
                else_=sim_score,
            )

        result = await self._db.execute(
            select(
                DocumentSegment,
                KnowledgeDocument.title,
                KnowledgeDocument.source_type,
                score_expr.label("fts_score"),
            )
            .join(KnowledgeDocument, DocumentSegment.document_id == KnowledgeDocument.id)
            .where(
                KnowledgeDocument.knowledge_base_id == kb_id,
                score_expr > 0,
            )
            .order_by(score_expr.desc())
            .limit(req.top_k)
        )
        rows = result.all()
        results = []
        for seg, title, src_type, fts_score in rows:
            results.append(KbSearchResult(
                segment_id=str(seg.id),
                document_id=str(seg.document_id),
                content=seg.content,
                score=float(fts_score),
                fulltext_score=float(fts_score),
                document_name=title,
                document_type="File" if src_type == "file" else "QaPair",
            ))
        return KbSearchResponse(results=results)

    async def _increment_recall_stats_async(self, document_ids: list[int]) -> None:
        """批量 UPSERT 召回统计 — 单次 INSERT ... ON CONFLICT 完成整批更新。

        使用独立的 AsyncSession，不共享请求 session，
        确保作为 fire-and-forget 任务运行时不会访问已关闭的 session。
        """
        try:
            async with AsyncSession(self._db.bind) as session:
                async with session.begin():
                    stmt = pg_insert(KnowledgeDocumentRecallStat).values([
                        {
                            "document_id": doc_id,
                            "recall_count": 1,
                            "last_recalled_at_utc": datetime.now(timezone.utc),
                        }
                        for doc_id in document_ids
                    ])
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["document_id"],
                        set_={
                            "recall_count": KnowledgeDocumentRecallStat.recall_count + 1,
                            "last_recalled_at_utc": datetime.now(timezone.utc),
                        },
                    )
                    await session.execute(stmt)
        except Exception as exc:
            logger.warning(f"Failed to update recall stats (fire-and-forget): {exc}")
