"""DocumentService — 文档 CRUD + 处理编排。

RAG 相关操作（分块、embedding、向量存储）全部委托给 retrieval_service，
本服务只负责业务编排和持久化。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.crud import create_entity, get_entity
from common.errors import NotFoundError
from ..models import (
    DocumentIndex,
    DocumentProcessingJob,
    DocumentSegment,
    IngestStatus,
    KnowledgeDocument,
    KnowledgeDocumentRecallStat,
    KnowledgeFolder,
)
from ..schemas import (
    KbDocumentView,
    KbSegmentView,
    ProcessingJobView,
    DocumentIndexView,
    QaCreateRequest,
    QaUpdateRequest,
    QaImportResult,
    QaImportError,
    TopRecalledKbDocumentView,
)

if __name__.startswith("backend.") or True:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ..retrieval_service import KnowledgeRetrievalService


class DocumentService:

    def __init__(self, db: AsyncSession, retrieval_service=None, queue=None):
        self._db = db
        self._retrieval = retrieval_service
        self._queue = queue

    # ── Document CRUD ──────────────────────────────────────────────

    async def list_documents(
        self,
        kb_id: int,
        page: int,
        page_size: int,
        folder_id: int | None = None,
        source_type: str | None = None,
    ) -> tuple[list[KbDocumentView], int]:
        query = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.knowledge_base_id == kb_id)
            .order_by(KnowledgeDocument.id.desc())
        )
        count_q = (
            select(func.count())
            .select_from(KnowledgeDocument)
            .where(KnowledgeDocument.knowledge_base_id == kb_id)
        )
        if folder_id is not None:
            if folder_id == 0:
                # folder_id=0 表示根目录（folder_id IS NULL）
                query = query.where(KnowledgeDocument.folder_id.is_(None))
                count_q = count_q.where(KnowledgeDocument.folder_id.is_(None))
            else:
                query = query.where(KnowledgeDocument.folder_id == folder_id)
                count_q = count_q.where(KnowledgeDocument.folder_id == folder_id)
        if source_type:
            query = query.where(KnowledgeDocument.source_type == source_type)
            count_q = count_q.where(KnowledgeDocument.source_type == source_type)

        total = (await self._db.execute(count_q)).scalar() or 0
        items = (
            await self._db.execute(query.offset((page - 1) * page_size).limit(page_size))
        ).scalars().all()

        # 批量获取 recall stats
        doc_ids = [d.id for d in items]
        recall_map = await self._batch_recall_stats(doc_ids)

        # 批量获取 folder path
        folder_ids = {d.folder_id for d in items if d.folder_id}
        folder_path_map = await self._batch_folder_paths(list(folder_ids))

        views = [
            self._to_doc_view(
                d,
                recall_count=recall_map.get(d.id, 0),
                last_recalled=recall_map.get(f"ts_{d.id}"),
                folder_path=folder_path_map.get(d.folder_id) if d.folder_id else None,
            )
            for d in items
        ]
        return views, total

    async def list_top_recalled_documents(
        self, kb_id: int, limit: int,
    ) -> list[TopRecalledKbDocumentView]:
        """按 recall_count 倒序返回被召回次数最多的文档。

        仅返回有召回统计记录（KnowledgeDocumentRecallStat）的文档，
        即真正发生过召回行为的文档；无召回记录的文档不出现在榜单中。
        """
        query = (
            select(KnowledgeDocument, KnowledgeDocumentRecallStat)
            .join(
                KnowledgeDocumentRecallStat,
                KnowledgeDocumentRecallStat.document_id == KnowledgeDocument.id,
            )
            .where(KnowledgeDocument.knowledge_base_id == kb_id)
            .order_by(
                KnowledgeDocumentRecallStat.recall_count.desc(),
                KnowledgeDocument.id.desc(),
            )
            .limit(limit)
        )
        rows = (await self._db.execute(query)).all()

        status_map = {
            "pending": "Pending", "processing": "Processing",
            "completed": "Completed", "failed": "Failed",
        }
        views: list[TopRecalledKbDocumentView] = []
        for doc, stat in rows:
            views.append(TopRecalledKbDocumentView(
                document_id=str(doc.id),
                knowledge_base_id=str(doc.knowledge_base_id),
                source_type="File" if doc.source_type == "file" else "QaPair",
                file_name=doc.source_uri,
                qa_question=doc.qa_question,
                ingest_status=status_map.get(doc.status, "Pending"),
                recall_count=stat.recall_count,
                last_recalled_at_utc=stat.last_recalled_at_utc.isoformat() if stat.last_recalled_at_utc else None,
                created_at_utc=doc.created_at_utc.isoformat() if doc.created_at_utc else "",
            ))
        return views

    async def get_document(self, kb_id: int, doc_id: int) -> KbDocumentView:
        doc = await self._get_doc(kb_id, doc_id)
        recall_count, last_recalled = await self._get_recall_stat(doc_id)
        folder_path = await self._get_folder_path(doc.folder_id) if doc.folder_id else None
        return self._to_doc_view(doc, recall_count, last_recalled, folder_path)

    async def upload_document(
        self,
        kb_id: int,
        file_content: bytes,
        file_name: str,
        content_type: str | None,
        file_size: int,
        folder_id: int | None,
        background_tasks=None,
    ) -> KbDocumentView:
        doc = await create_entity(
            self._db,
            KnowledgeDocument,
            knowledge_base_id=kb_id,
            folder_id=folder_id,
            title=file_name,
            source_type="file",
            source_uri=file_name,
            content_type=content_type,
            file_size=file_size,
            status=IngestStatus.PENDING,
        )
        await self._db.commit()

        if self._retrieval is not None and background_tasks is not None:
            self._trigger_processing(background_tasks, kb_id, doc.id, file_content, file_name, content_type or "")

        return self._to_doc_view(doc)

    async def create_qa(
        self,
        kb_id: int,
        req: QaCreateRequest,
        background_tasks=None,
    ) -> KbDocumentView:
        answer = req.answer
        doc = await create_entity(
            self._db,
            KnowledgeDocument,
            knowledge_base_id=kb_id,
            folder_id=int(req.folder_id) if req.folder_id else None,
            title=req.question[:200],
            source_type="qa",
            content=answer,
            qa_question=req.question,
            status=IngestStatus.PENDING,
        )
        await self._db.commit()

        if self._retrieval is not None and background_tasks is not None and answer:
            self._trigger_processing(
                background_tasks, kb_id, doc.id,
                answer.encode("utf-8"),
                f"{req.question[:50]}.txt",
                "text/plain",
            )

        return self._to_doc_view(doc)

    async def update_qa(self, kb_id: int, doc_id: int, req: QaUpdateRequest) -> KbDocumentView:
        doc = await self._get_doc(kb_id, doc_id)
        if doc.source_type != "qa":
            raise ValueError("Only QA documents can be updated via this endpoint")
        if req.question is not None:
            doc.qa_question = req.question
            doc.title = req.question[:200]
        if req.answer is not None:
            doc.content = req.answer
        await self._db.commit()
        return self._to_doc_view(doc)

    async def delete_document(self, kb_id: int, doc_id: int) -> None:
        """删除文档 — 先调 retrieval 清理向量，FK CASCADE 清理子表。"""
        doc = await self._get_doc(kb_id, doc_id)

        # 委托 retrieval service 清理向量和 segments
        if self._retrieval is not None:
            try:
                await self._retrieval.aremove_document(str(kb_id), str(doc_id))
            except Exception as exc:
                logger.warning(f"Failed to clean retrieval data for doc {doc_id}: {exc}")

        await self._db.delete(doc)
        await self._db.commit()

    async def move_document(self, kb_id: int, doc_id: int, target_folder_id: int | None) -> None:
        doc = await self._get_doc(kb_id, doc_id)
        if target_folder_id is not None:
            folder = await self._db.get(KnowledgeFolder, target_folder_id)
            if folder is None or folder.knowledge_base_id != kb_id:
                raise NotFoundError("KnowledgeFolder", str(target_folder_id))
        doc.folder_id = target_folder_id
        await self._db.commit()

    async def reindex_document(self, kb_id: int, doc_id: int, background_tasks=None) -> None:
        """重新索引：重置状态 + 重新触发处理。需要重新读取文件内容。"""
        doc = await self._get_doc(kb_id, doc_id)
        if doc.status not in (IngestStatus.COMPLETED, IngestStatus.FAILED):
            raise ValueError(f"Cannot reindex document in status '{doc.status}'")

        # 清理旧数据
        if self._retrieval is not None:
            try:
                await self._retrieval.aremove_document(str(kb_id), str(doc_id))
            except Exception as exc:
                logger.warning(f"Failed to clean old retrieval data for reindex: {exc}")

        # 重置状态
        doc.status = IngestStatus.PENDING
        doc.ingest_error = None
        await self._db.commit()

        # 重新触发 — 需要 file_bytes，这里用 content 字段作为降级
        if self._retrieval is not None and background_tasks is not None:
            content_bytes = (doc.content or "").encode("utf-8")
            self._trigger_processing(
                background_tasks, kb_id, doc_id,
                content_bytes,
                doc.source_uri or f"{doc.id}.txt",
                doc.content_type or "text/plain",
            )

    async def bulk_import_qa(
        self, kb_id: int, qa_pairs: list[dict], background_tasks=None,
    ) -> QaImportResult:
        """批量导入 QA 对。qa_pairs: [{"question": ..., "answer": ...}, ...]"""
        result = QaImportResult()
        for i, pair in enumerate(qa_pairs):
            q = pair.get("question", "").strip()
            a = pair.get("answer", "").strip()
            if not q or not a:
                result.skipped_count += 1
                result.errors.append(QaImportError(
                    row_number=i + 1,
                    question=q or None,
                    error_code="missing_field",
                    message="Question and answer are required",
                ))
                continue
            try:
                req = QaCreateRequest(question=q, answer=a)
                await self.create_qa(kb_id, req, background_tasks)
                result.created_count += 1
            except Exception as exc:
                result.skipped_count += 1
                result.errors.append(QaImportError(
                    row_number=i + 1,
                    question=q,
                    error_code="create_failed",
                    message=str(exc),
                ))
        return result

    # ── Segments ───────────────────────────────────────────────────

    async def list_segments(
        self, kb_id: int, doc_id: int, page: int, page_size: int,
    ) -> tuple[list[KbSegmentView], int]:
        await self._get_doc(kb_id, doc_id)
        query = (
            select(DocumentSegment)
            .where(DocumentSegment.document_id == doc_id)
            .order_by(DocumentSegment.segment_index)
        )
        total = (await self._db.execute(
            select(func.count()).select_from(DocumentSegment).where(
                DocumentSegment.document_id == doc_id,
            )
        )).scalar() or 0
        items = (
            await self._db.execute(query.offset((page - 1) * page_size).limit(page_size))
        ).scalars().all()
        return [self._to_segment_view(s) for s in items], total

    async def get_segment(self, kb_id: int, doc_id: int, seg_id: int) -> KbSegmentView:
        await self._get_doc(kb_id, doc_id)
        seg = await self._db.get(DocumentSegment, seg_id)
        if seg is None or seg.document_id != doc_id:
            raise NotFoundError("DocumentSegment", str(seg_id))
        return self._to_segment_view(seg)

    # ── Processing Jobs ────────────────────────────────────────────

    async def list_processing_jobs(self, kb_id: int) -> list[ProcessingJobView]:
        result = await self._db.execute(
            select(DocumentProcessingJob)
            .join(KnowledgeDocument, DocumentProcessingJob.document_id == KnowledgeDocument.id)
            .where(KnowledgeDocument.knowledge_base_id == kb_id)
            .order_by(DocumentProcessingJob.id.desc())
        )
        return [self._to_job_view(j) for j in result.scalars().all()]

    async def get_document_processing(
        self, kb_id: int, doc_id: int,
    ) -> ProcessingJobView | None:
        await self._get_doc(kb_id, doc_id)
        result = await self._db.execute(
            select(DocumentProcessingJob)
            .where(DocumentProcessingJob.document_id == doc_id)
            .order_by(DocumentProcessingJob.id.desc())
            .limit(1)
        )
        job = result.scalar_one_or_none()
        return self._to_job_view(job) if job else None

    # ── Document Indexes ───────────────────────────────────────────

    async def list_document_indexes(
        self, kb_id: int, doc_id: int,
    ) -> list[DocumentIndexView]:
        await self._get_doc(kb_id, doc_id)
        result = await self._db.execute(
            select(DocumentIndex)
            .where(DocumentIndex.document_id == doc_id)
            .order_by(DocumentIndex.id)
        )
        return [self._to_index_view(ix) for ix in result.scalars().all()]

    # ── Internal: processing trigger ───────────────────────────────

    def _trigger_processing(self, background_tasks, kb_id, doc_id, file_bytes, file_name, content_type):
        """委托给 processing 模块在后台执行。优先使用队列，降级到 BackgroundTask。"""
        from ..processing import enqueue_document_processing, process_document
        from alkit_db.engine import get_session_factory

        if self._queue is not None:
            # Queue 模式：异步 enqueue，不阻塞当前请求
            import asyncio
            asyncio.get_running_loop().create_task(
                enqueue_document_processing(
                    self._queue,
                    kb_id=kb_id,
                    doc_id=doc_id,
                    file_bytes=file_bytes,
                    file_name=file_name,
                    content_type=content_type,
                )
            )
        else:
            # 降级：直接用 BackgroundTask
            background_tasks.add_task(
                process_document,
                kb_id=kb_id,
                doc_id=doc_id,
                file_bytes=file_bytes,
                file_name=file_name,
                content_type=content_type,
                retrieval_service=self._retrieval,
                session_factory=get_session_factory(),
            )

    # ── Internal: helpers ──────────────────────────────────────────

    async def _get_doc(self, kb_id: int, doc_id: int) -> KnowledgeDocument:
        doc = await self._db.get(KnowledgeDocument, doc_id)
        if doc is None or doc.knowledge_base_id != kb_id:
            raise NotFoundError("KnowledgeDocument", str(doc_id))
        return doc

    async def _get_recall_stat(self, doc_id: int) -> tuple[int, datetime | None]:
        result = await self._db.execute(
            select(KnowledgeDocumentRecallStat)
            .where(KnowledgeDocumentRecallStat.document_id == doc_id)
        )
        stat = result.scalar_one_or_none()
        if stat:
            return stat.recall_count, stat.last_recalled_at_utc
        return 0, None

    async def _batch_recall_stats(self, doc_ids: list[int]) -> dict:
        if not doc_ids:
            return {}
        result = await self._db.execute(
            select(KnowledgeDocumentRecallStat)
            .where(KnowledgeDocumentRecallStat.document_id.in_(doc_ids))
        )
        stats = result.scalars().all()
        m = {}
        for s in stats:
            m[s.document_id] = s.recall_count
            m[f"ts_{s.document_id}"] = s.last_recalled_at_utc
        return m

    async def _batch_folder_paths(self, folder_ids: list[int]) -> dict[int, str]:
        if not folder_ids:
            return {}
        # 简化：直接返回文件夹名称；完整实现需递归拼接路径
        result = await self._db.execute(
            select(KnowledgeFolder).where(KnowledgeFolder.id.in_(folder_ids))
        )
        return {f.id: f.name for f in result.scalars().all()}

    async def _get_folder_path(self, folder_id: int) -> str:
        folder = await self._db.get(KnowledgeFolder, folder_id)
        return folder.name if folder else ""

    # ── ORM → Schema mapping ──────────────────────────────────────

    @staticmethod
    def _to_doc_view(
        doc: KnowledgeDocument,
        recall_count: int = 0,
        last_recalled: datetime | None = None,
        folder_path: str | None = None,
    ) -> KbDocumentView:
        source_type = "File" if doc.source_type == "file" else "QaPair"
        status_map = {
            "pending": "Pending", "processing": "Processing",
            "completed": "Completed", "failed": "Failed",
        }
        return KbDocumentView(
            id=str(doc.id),
            knowledge_base_id=str(doc.knowledge_base_id),
            source_type=source_type,
            stored_file_id=doc.stored_file_id,
            file_name=doc.source_uri,
            content_type=doc.content_type,
            file_size=doc.file_size if doc.file_size else None,
            qa_question=doc.qa_question,
            qa_answer=doc.content if doc.source_type == "qa" else None,
            ingest_status=status_map.get(doc.status, "Pending"),
            ingest_error=doc.ingest_error,
            ingested_at_utc=doc.ingested_at_utc.isoformat() if doc.ingested_at_utc else None,
            metadata_json=json.dumps(doc.extra_json) if doc.extra_json else None,
            recall_count=recall_count,
            last_recalled_at_utc=last_recalled.isoformat() if last_recalled else None,
            created_at_utc=doc.created_at_utc.isoformat() if doc.created_at_utc else "",
            updated_at_utc=doc.updated_at_utc.isoformat() if doc.updated_at_utc else None,
            folder_id=str(doc.folder_id) if doc.folder_id else None,
            folder_path=folder_path,
        )

    @staticmethod
    def _to_segment_view(seg: DocumentSegment) -> KbSegmentView:
        return KbSegmentView(
            id=str(seg.id),
            document_id=str(seg.document_id),
            segment_index=seg.segment_index,
            content=seg.content,
            metadata_json=json.dumps(seg.extra_json) if seg.extra_json else None,
            created_at_utc=seg.created_at_utc.isoformat() if seg.created_at_utc else "",
            updated_at_utc=seg.updated_at_utc.isoformat() if seg.updated_at_utc else None,
        )

    @staticmethod
    def _to_job_view(job: DocumentProcessingJob) -> ProcessingJobView:
        return ProcessingJobView(
            id=str(job.id),
            document_id=str(job.document_id),
            current_stage=job.current_stage or job.job_type,
            stage_progress_json=json.dumps(job.stage_progress_json) if job.stage_progress_json else None,
            error_message=job.error_message,
            started_at_utc=job.started_at_utc.isoformat() if job.started_at_utc else None,
            completed_at_utc=job.completed_at_utc.isoformat() if job.completed_at_utc else None,
            created_at_utc=job.created_at_utc.isoformat() if job.created_at_utc else "",
            updated_at_utc=job.updated_at_utc.isoformat() if job.updated_at_utc else None,
        )

    @staticmethod
    def _to_index_view(ix: DocumentIndex) -> DocumentIndexView:
        type_map = {"embedding": "Vector", "fulltext": "FullText", "graph": "Graph"}
        return DocumentIndexView(
            id=str(ix.id),
            document_id=str(ix.document_id) if ix.document_id else "",
            index_type=type_map.get(ix.index_type, ix.index_type),
            status=ix.status,
            config_json=json.dumps(ix.config_json) if ix.config_json else None,
            stats_json=json.dumps(ix.stats_json) if ix.stats_json else None,
            built_at_utc=ix.built_at_utc.isoformat() if ix.built_at_utc else None,
            created_at_utc=ix.created_at_utc.isoformat() if ix.created_at_utc else "",
            updated_at_utc=ix.updated_at_utc.isoformat() if ix.updated_at_utc else None,
        )
