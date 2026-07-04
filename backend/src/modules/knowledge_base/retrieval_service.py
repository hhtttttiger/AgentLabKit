"""KnowledgeRetrievalService — 连接 backend 持久化层与 retrieval 包的核心桥接层

实现 retrieval.interface.BaseRetrievalService，编排：
- DocumentProcessor（文档处理 pipeline）— 来自 retrieval 包
- BaseEmbeddingProvider（向量生成）— 来自 retrieval 包
- BaseVectorStore（向量持久化与检索）— 来自 retrieval 包
- SQLAlchemy（segment 持久化）

本服务是知识库模块与 RAG 包之间的适配器：
- 知识库模块只做 CRUD 和业务编排
- 所有 RAG 逻辑（分块、embedding、向量检索）全部委托 retrieval 包
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone

from loguru import logger
from typing import List, Literal, Optional

from sqlalchemy import delete, select

from retrieval.interface import BaseRetrievalService, ProcessingResult
from retrieval.model import (
    DocumentSource,
    Segment,
    SegmentSetting,
    SearchResult,
)
from retrieval.providers.embedding import BaseEmbeddingProvider
from retrieval.stores.base import BaseVectorStore, VectorRecord
from retrieval.engines.local_engine.processing import DocumentProcessor, StepProgressCallback

from .models import (
    DocumentIndex,
    DocumentSegment,
    KnowledgeDocument,
    SegmentEmbedding,
)

SearchMode = Literal["hybrid", "vector", "fulltext"]


def _utcnow() -> datetime:
    """Naive UTC now：知识库 *_utc 列为 TIMESTAMP WITHOUT TIME ZONE（迁移
    0003），写入必须 naive，否则 asyncpg 报 offset-naive/aware 冲突。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class KnowledgeRetrievalService(BaseRetrievalService):
    """知识库级检索服务 — backend 与 retrieval 包之间的适配器。

    由 backend 的 FastAPI lifespan 实例化，
    通过 app.state.retrieval_service 注入。
    """

    def __init__(
        self,
        session_factory,
        embedding_provider: BaseEmbeddingProvider,
        vector_store: BaseVectorStore,
    ):
        self._db = session_factory
        self._embedding = embedding_provider
        self._vector_store = vector_store
        self._embedding_provider = embedding_provider

    @property
    def embedding_provider(self) -> BaseEmbeddingProvider:
        """Public accessor for the embedding provider (e.g. for memory module)."""
        return self._embedding_provider

    # ------------------------------------------------------------------
    # 索引文档
    # ------------------------------------------------------------------

    async def aindex_document(
        self,
        kb_id: str,
        doc_id: str,
        source: DocumentSource,
        setting: Optional[SegmentSetting] = None,
        on_step_change: Optional[StepProgressCallback] = None,
    ) -> ProcessingResult:
        """处理并索引单个文档到知识库

        事务安全：segments + embeddings + doc status 在同一事务中提交，
        失败时全部回滚，不留孤儿数据。支持幂等 re-index。
        """
        if setting is None:
            setting = SegmentSetting()

        # 1. 委托 retrieval 包处理文档（纯计算，不涉及 DB）
        processor = DocumentProcessor(
            embedding_provider=self._embedding_provider,
            on_step_change=on_step_change,
        )
        result = await processor.aprocess(source, setting)

        if not result.success:
            logger.error(f"Document processing failed for doc {doc_id}: {result.error_message}")
            await self._update_doc_status(doc_id, "failed", error=result.error_message)
            return result

        # 2. 幂等 re-index：先清理旧数据
        await self._vector_store.adelete_by_document(kb_id, doc_id)

        # 3. 单事务：segments + embeddings + doc status + index records
        try:
            db_segment_ids: list[int] = []
            async with self._db() as session:
                async with session.begin():
                    # 3a. 清理旧 segments（幂等）
                    await session.execute(
                        delete(DocumentSegment).where(
                            DocumentSegment.document_id == int(doc_id)
                        )
                    )

                    # 3b. 插入新 segments，flush 获取雪花 ID
                    for idx, seg in enumerate(result.segments):
                        db_segment = DocumentSegment(
                            document_id=int(doc_id),
                            segment_index=idx,
                            content=seg.text,
                            extra_json={
                                "keywords": seg.keywords,
                                "word_segmentation": seg.word_segmentation,
                                "detected_script": seg.detected_script,
                                "metadata": seg.metadata,
                            },
                        )
                        session.add(db_segment)
                        await session.flush()
                        db_segment_ids.append(db_segment.id)

                    # 3c. 生成 embeddings（在事务内，但 session 闲置等待 IO）
                    if result.segments:
                        texts = [seg.text for seg in result.segments]
                        embedding_results = await self._embedding.aembed_batch(texts)

                        # 3d. 写入向量记录
                        records = []
                        for seg, emb, db_id in zip(result.segments, embedding_results, db_segment_ids):
                            if emb.vector:
                                records.append(
                                    VectorRecord(
                                        id=str(db_id),
                                        vector=emb.vector,
                                        metadata={
                                            "document_id": doc_id,
                                            "model": emb.model,
                                        },
                                    )
                                )
                        if records:
                            await self._vector_store.aupsert(kb_id, records, session=session)

                    # 3e. 更新文档状态
                    doc = await session.get(KnowledgeDocument, int(doc_id))
                    if doc:
                        doc.status = "completed"
                        doc.segment_count = len(result.segments)
                        doc.ingested_at_utc = _utcnow()

                    # 3f. 记录 DocumentIndex
                    for idx_type in (setting.indexes or ["embedding"]):
                        index = DocumentIndex(
                            knowledge_base_id=int(kb_id),
                            document_id=int(doc_id),
                            index_name=f"{idx_type}_{doc_id}",
                            index_type=idx_type,
                            status="completed",
                            built_at_utc=_utcnow(),
                        )
                        session.add(index)

            logger.info(
                f"Indexed doc {doc_id}: {len(result.segments)} segments, "
                f"{len(db_segment_ids)} embeddings in KB {kb_id}"
            )

        except Exception as exc:
            logger.error(f"Indexing failed for doc {doc_id}: {exc}")
            await self._update_doc_status(doc_id, "failed", error=str(exc))

        return result

    # ------------------------------------------------------------------
    # 删除文档
    # ------------------------------------------------------------------

    async def aremove_document(self, kb_id: str, doc_id: str) -> bool:
        """从知识库中移除文档的所有分段和向量"""
        int_doc_id = int(doc_id)
        int_kb_id = int(kb_id)

        async with self._db() as session:
            # 1. 获取 segment IDs
            seg_result = await session.execute(
                select(DocumentSegment.id).where(
                    DocumentSegment.document_id == int_doc_id
                )
            )
            segment_ids = [str(row[0]) for row in seg_result.all()]

            # 2. 委托 retrieval 包删除向量
            if segment_ids:
                try:
                    await self._vector_store.adelete(kb_id, segment_ids)
                except Exception as exc:
                    logger.warning(f"Failed to delete embeddings for doc {doc_id}: {exc}")

            # 3. 删除 segments（FK CASCADE 也会处理，这里显式清理确保一致性）
            await session.execute(
                delete(DocumentSegment).where(
                    DocumentSegment.document_id == int_doc_id
                )
            )

            # 4. 删除 document_indexes
            await session.execute(
                delete(DocumentIndex).where(
                    DocumentIndex.document_id == int_doc_id
                )
            )

            # 5. 更新文档状态
            doc = await session.get(KnowledgeDocument, int_doc_id)
            if doc:
                doc.status = "pending"
                doc.segment_count = 0
                doc.ingested_at_utc = None

            await session.commit()

        logger.info(f"Removed document {doc_id} from KB {kb_id}")
        return True

    # ------------------------------------------------------------------
    # 检索 — 支持 vector / fulltext / hybrid 三种模式
    # ------------------------------------------------------------------

    async def asearch(
        self,
        kb_id: str,
        query: str,
        top_k: int = 5,
        search_mode: SearchMode = "hybrid",
        **kwargs,
    ) -> List[SearchResult]:
        """在知识库中跨文档检索

        search_mode:
          - "vector": 纯向量余弦相似度
          - "fulltext": pg_trgm 全文检索
          - "hybrid": 向量 + 全文 RRF 融合（默认）
        """
        if search_mode == "vector":
            return await self._search_vector(kb_id, query, top_k)
        elif search_mode == "fulltext":
            return await self._search_fulltext(kb_id, query, top_k)
        else:
            return await self._search_hybrid(kb_id, query, top_k)

    async def _search_vector(
        self, kb_id: str, query: str, top_k: int
    ) -> List[SearchResult]:
        """纯向量检索"""
        try:
            query_embedding = await self._embedding.aembed(query)
            if not query_embedding.vector:
                logger.warning(f"Empty embedding for query: {query[:50]}")
                return []

            vector_results = await self._vector_store.aquery(
                kb_id, query_embedding.vector, top_k=top_k
            )
        except Exception as exc:
            logger.error(f"Vector search failed for KB {kb_id}: {exc}")
            return []

        return await self._load_segments(kb_id, vector_results, top_k)

    async def _search_fulltext(
        self, kb_id: str, query: str, top_k: int
    ) -> List[SearchResult]:
        """pg_trgm 全文检索"""
        try:
            fts_results = await self._vector_store.aquery_fulltext(
                kb_id, query, top_k=top_k
            )
        except Exception as exc:
            logger.error(f"Fulltext search failed for KB {kb_id}: {exc}")
            return []

        return await self._load_segments(kb_id, fts_results, top_k)

    async def _search_hybrid(
        self, kb_id: str, query: str, top_k: int
    ) -> List[SearchResult]:
        """RRF 融合检索：向量 + 全文并行，Reciprocal Rank Fusion 合并"""
        recall_k = top_k * 3  # 过量召回用于融合

        # 并行执行向量检索和全文检索
        vector_task = self._search_vector_raw(kb_id, query, recall_k)
        fts_task = self._vector_store.aquery_fulltext(kb_id, query, top_k=recall_k)

        vector_results, fts_results = await asyncio.gather(
            vector_task, fts_task, return_exceptions=True
        )

        if isinstance(vector_results, Exception):
            logger.warning(f"Vector search failed in hybrid mode: {vector_results}")
            vector_results = []
        if isinstance(fts_results, Exception):
            logger.warning(f"FTS search failed in hybrid mode: {fts_results}")
            fts_results = []

        # RRF 融合
        rrf_k = 60  # 标准常数
        scores: dict[str, float] = defaultdict(float)
        vector_score_map: dict[str, float] = {}
        fts_score_map: dict[str, float] = {}

        for rank, r in enumerate(vector_results):
            scores[r.id] += 1.0 / (rrf_k + rank)
            vector_score_map[r.id] = r.score

        for rank, r in enumerate(fts_results):
            scores[r.id] += 1.0 / (rrf_k + rank)
            fts_score_map[r.id] = r.score

        if not scores:
            return []

        # 按 RRF 分数排序，取 top_k
        ranked_ids = sorted(scores, key=lambda x: -scores[x])[:top_k]

        # 加载 segment 文本
        segment_ids = [int(sid) for sid in ranked_ids]
        async with self._db() as session:
            seg_stmt = (
                select(DocumentSegment, KnowledgeDocument.id, KnowledgeDocument.source_type, KnowledgeDocument.title)
                .join(KnowledgeDocument, DocumentSegment.document_id == KnowledgeDocument.id)
                .where(DocumentSegment.id.in_(segment_ids))
            )
            rows = (await session.execute(seg_stmt)).all()

        seg_map = {str(seg.id): (seg, str(doc_id), source_type, title or "") for seg, doc_id, source_type, title in rows}

        results: List[SearchResult] = []
        for sid in ranked_ids:
            entry = seg_map.get(sid)
            if entry is None:
                continue
            seg, doc_id, source_type, title = entry
            results.append(
                SearchResult(
                    id=str(seg.id),
                    text=seg.content,
                    source=title,
                    score=round(scores[sid], 6),
                    metadata={
                        **(seg.extra_json.get("metadata", {}) if seg.extra_json else {}),
                        "document_id": doc_id,
                        "document_type": "File" if source_type == "file" else "QaPair",
                        "vector_score": vector_score_map.get(sid, 0.0),
                        "fulltext_score": fts_score_map.get(sid, 0.0),
                    },
                )
            )

        return results

    async def _search_vector_raw(
        self, kb_id: str, query: str, top_k: int
    ):
        """向量检索，返回 VectorSearchResult（不做 segment 加载）"""
        query_embedding = await self._embedding.aembed(query)
        if not query_embedding.vector:
            return []
        return await self._vector_store.aquery(
            kb_id, query_embedding.vector, top_k=top_k
        )

    async def _load_segments(
        self, kb_id: str, search_results, top_k: int
    ) -> List[SearchResult]:
        """从 VectorSearchResult 加载 segment 文本，组装 SearchResult"""
        if not search_results:
            return []

        segment_ids = [int(r.id) for r in search_results]
        score_map = {r.id: r.score for r in search_results}

        async with self._db() as session:
            seg_stmt = (
                select(DocumentSegment, KnowledgeDocument.id, KnowledgeDocument.source_type, KnowledgeDocument.title)
                .join(KnowledgeDocument, DocumentSegment.document_id == KnowledgeDocument.id)
                .where(DocumentSegment.id.in_(segment_ids))
            )
            rows = (await session.execute(seg_stmt)).all()

        seg_map = {str(seg.id): (seg, str(doc_id), source_type, title or "") for seg, doc_id, source_type, title in rows}

        results: List[SearchResult] = []
        for vr in search_results:
            entry = seg_map.get(vr.id)
            if entry is None:
                continue
            seg, doc_id, source_type, title = entry
            results.append(
                SearchResult(
                    id=str(seg.id),
                    text=seg.content,
                    source=title,
                    score=round(score_map.get(vr.id, 0.0), 6),
                    metadata={
                        **(seg.extra_json.get("metadata", {}) if seg.extra_json else {}),
                        "document_id": doc_id,
                        "document_type": "File" if source_type == "file" else "QaPair",
                    },
                )
            )

        return results[:top_k]

    async def asearch_multi(
        self, kb_ids: List[str], query: str, top_k: int = 5, search_mode: SearchMode = "hybrid"
    ) -> List[SearchResult]:
        """搜索多个知识库 — 并行执行，合并排序。"""
        per_kb_k = max(top_k // max(len(kb_ids), 1), 3)

        tasks = [
            self.asearch(kb_id, query, top_k=per_kb_k, search_mode=search_mode)
            for kb_id in kb_ids
        ]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        all_results: List[SearchResult] = []
        for r in batch_results:
            if isinstance(r, Exception):
                logger.warning(f"Multi-KB search partial failure: {r}")
                continue
            if isinstance(r, list):
                all_results.extend(r)

        all_results.sort(key=lambda r: -r.score)
        return all_results[:top_k]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _update_doc_status(
        self, doc_id: str, status: str, error: str | None = None
    ) -> None:
        """更新文档处理状态。"""
        try:
            async with self._db() as session:
                doc = await session.get(KnowledgeDocument, int(doc_id))
                if doc:
                    doc.status = status
                    if error:
                        doc.ingest_error = error[:2000] if error else None
                    await session.commit()
        except Exception as exc:
            logger.error(f"Failed to update doc status: {exc}")
