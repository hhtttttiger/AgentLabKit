"""后台文档处理 — 上传后触发 RAG pipeline。

支持两种模式：
1. Queue 模式（生产）：通过 Redis Streams 队列异步处理，支持重试、死信
2. BackgroundTask 模式（降级）：直接在进程内处理，无持久化

编排流程：
1. 创建 ProcessingJob 记录
2. 委托 retrieval_service 处理文档（分块 + embedding + 向量存储）
3. 更新 ProcessingJob 状态
"""

from __future__ import annotations

import asyncio
import json
import base64
from datetime import datetime, timezone
from dataclasses import dataclass

from loguru import logger
from typing import TYPE_CHECKING

from pydantic import BaseModel

from retrieval.model import DocumentSource, SegmentSetting

from .models import (
    DocumentProcessingJob,
    IngestStatus,
    JobStatus,
    KnowledgeDocument,
)

if TYPE_CHECKING:
    from .retrieval_service import KnowledgeRetrievalService
    from retrieval.providers.file_storage import BaseFileStorage

def _utcnow() -> datetime:
    """Naive UTC now：document_processing_jobs 的 *_utc 列是 TIMESTAMP WITHOUT
    TIME ZONE（迁移 0003 对齐为 NOTZ），写入必须 naive，否则 asyncpg 报
    offset-naive/aware 冲突。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Pipeline 步骤名（与 retrieval DocumentProcessor 一致）
_PIPELINE_STEP_NAMES = [
    "DocumentLoaderStep",
    "DocumentSplitterStep",
    "TokenizerStep",
    "TerminologyStep",
    "GCStep",
    "IndexBuilderStep",
    "GraphBuilderStep",
]

# ── Queue-based processing ────────────────────────────────────────────

QUEUE_NAME = "document_processing"

# 消息契约版本。向后兼容地新增字段；发生 breaking 变更时递增，
# 由消费端拒绝不兼容版本（→ 重试/死信），避免静默的错误处理。
_DOCUMENT_PROCESSING_PAYLOAD_VERSION = 1


class DocumentProcessingPayload(BaseModel):
    """web(生产者) → worker(消费者) 之间的消息契约。

    跨进程通信必须有显式、可演化的契约：新增字段保持向后兼容，
    breaking 变更时递增 ``version`` 并由消费端拒绝旧版本。
    """

    version: int = _DOCUMENT_PROCESSING_PAYLOAD_VERSION
    kb_id: int
    doc_id: int
    file_bytes_b64: str | None = None  # 降级：无 file_storage 时传递原始字节
    stored_file_id: str | None = None   # 优先：通过 file_storage 取回
    file_name: str
    content_type: str


@dataclass
class _ProcessingContext:
    """Holds runtime dependencies for the queue consumer handler."""
    retrieval_service: KnowledgeRetrievalService
    session_factory: object
    file_storage: BaseFileStorage | None = None


_processing_ctx: _ProcessingContext | None = None


def init_processing_context(
    retrieval_service: KnowledgeRetrievalService,
    session_factory: object,
    file_storage: BaseFileStorage | None = None,
) -> None:
    """Called during lifespan to set up the processing context."""
    global _processing_ctx
    _processing_ctx = _ProcessingContext(
        retrieval_service=retrieval_service,
        session_factory=session_factory,
        file_storage=file_storage,
    )


async def enqueue_document_processing(
    queue,
    *,
    kb_id: int,
    doc_id: int,
    file_bytes: bytes | None = None,
    stored_file_id: str | None = None,
    file_name: str,
    content_type: str,
) -> None:
    """Publish a document processing message to the queue.

    优先传递 stored_file_id（consumer 端从 file_storage 取回），
    降级时传递 file_bytes_b64（向后兼容）。
    """
    from alkit_infra.queue.message import Message

    payload = DocumentProcessingPayload(
        kb_id=kb_id,
        doc_id=doc_id,
        file_bytes_b64=base64.b64encode(file_bytes).decode("ascii") if file_bytes else None,
        stored_file_id=stored_file_id,
        file_name=file_name,
        content_type=content_type,
    )
    msg = Message(topic=QUEUE_NAME, payload=payload.model_dump_json())
    await queue.publish(QUEUE_NAME, msg)
    logger.info(f"Enqueued document processing for doc {doc_id} (kb {kb_id})")


async def handle_queue_message(message) -> None:
    """Queue consumer handler — processes a single document processing message.

    ``QueueConsumer`` 调用本函数时只传 ``message``（单参，见 consumer._process_message）。
    """
    if _processing_ctx is None:
        logger.error("Processing context not initialized, rejecting message")
        raise RuntimeError("Processing context not initialized")

    payload = DocumentProcessingPayload.model_validate_json(message.payload)
    if payload.version != _DOCUMENT_PROCESSING_PAYLOAD_VERSION:
        # 不兼容版本：抛异常让队列走重试/死信，而不是静默处理。
        raise RuntimeError(
            f"Unsupported payload version {payload.version}, "
            f"expected {_DOCUMENT_PROCESSING_PAYLOAD_VERSION}"
        )

    # 优先：通过 stored_file_id 从 file_storage 取回文件
    file_bytes: bytes | None = None
    if payload.stored_file_id and _processing_ctx.file_storage:
        try:
            file_bytes = await _processing_ctx.file_storage.retrieve(payload.stored_file_id)
        except Exception as exc:
            logger.warning(f"Failed to retrieve file {payload.stored_file_id}, falling back to payload bytes: {exc}")

    # 降级：从 payload 中解码 base64 字节
    if file_bytes is None and payload.file_bytes_b64:
        file_bytes = base64.b64decode(payload.file_bytes_b64)

    if file_bytes is None:
        logger.error(f"No file content available for doc {payload.doc_id}")
        # 标记文档为 FAILED，防止永久卡在 PENDING
        async with _processing_ctx.session_factory() as session:
            doc = await session.get(KnowledgeDocument, payload.doc_id)
            if doc and doc.status not in (IngestStatus.COMPLETED, IngestStatus.FAILED):
                doc.status = IngestStatus.FAILED
                doc.ingest_error = "File content not available (storage retrieval failed)"
                await session.commit()
        return

    await process_document(
        kb_id=payload.kb_id,
        doc_id=payload.doc_id,
        file_bytes=file_bytes,
        file_name=payload.file_name,
        content_type=payload.content_type,
        retrieval_service=_processing_ctx.retrieval_service,
        session_factory=_processing_ctx.session_factory,
    )


# ── Core processing logic (shared by both modes) ─────────────────────


async def process_document(
    kb_id: int,
    doc_id: int,
    file_bytes: bytes,
    file_name: str,
    content_type: str,
    retrieval_service: KnowledgeRetrievalService,
    session_factory,
    setting: SegmentSetting | None = None,
) -> bool:
    """处理单个文档：建索引 + 生成 embedding。"""
    # ── 幂等保护：检查文档状态 ──
    async with session_factory() as session:
        doc = await session.get(KnowledgeDocument, doc_id)
        if doc is None:
            logger.error(f"Document {doc_id} not found, skipping processing")
            return False
        if doc.status == IngestStatus.PROCESSING:
            logger.info(f"Document {doc_id} is already being processed, skipping")
            return False
        # 标记为处理中
        doc.status = IngestStatus.PROCESSING
        await session.commit()

    # ── 创建 ProcessingJob ──
    job_id: int | None = None
    async with session_factory() as session:
        job = DocumentProcessingJob(
            document_id=doc_id,
            job_type="index",
            status=JobStatus.RUNNING,
            started_at_utc=_utcnow(),
        )
        session.add(job)
        await session.flush()
        job_id = job.id
        await session.commit()

    # ── 初始化步骤进度 ──
    stage_progress = [
        {"name": name, "status": "pending", "startedAt": None, "endedAt": None}
        for name in _PIPELINE_STEP_NAMES
    ]

    _loop: asyncio.AbstractEventLoop | None = None
    try:
        _loop = asyncio.get_running_loop()
    except RuntimeError:
        pass

    def _on_step_change(step_name: str, step_index: int, total: int, status: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        if status == "running":
            stage_progress[step_index]["status"] = "running"
            stage_progress[step_index]["startedAt"] = now
        elif status in ("done", "failed"):
            stage_progress[step_index]["status"] = status
            stage_progress[step_index]["endedAt"] = now

        if _loop is not None and _loop.is_running():
            _loop.call_soon_threadsafe(
                _loop.create_task,
                _update_job_progress(session_factory, job_id, step_name, stage_progress),
            )

    try:
        source = DocumentSource(
            content=file_bytes,
            file_name=file_name,
            content_type=content_type,
        )

        result = await retrieval_service.aindex_document(
            kb_id=str(kb_id),
            doc_id=str(doc_id),
            source=source,
            setting=setting,
            on_step_change=_on_step_change,
        )

        async with session_factory() as session:
            job = await session.get(DocumentProcessingJob, job_id)
            if job:
                job.status = JobStatus.COMPLETED if result.success else JobStatus.FAILED
                job.error_message = result.error_message if not result.success else None
                job.completed_at_utc = _utcnow()
                job.current_stage = "Completed" if result.success else "Failed"
                job.stage_progress_json = stage_progress
                await session.commit()

        return result.success

    except Exception as exc:
        logger.exception(f"Document processing failed for doc {doc_id}: {exc}")

        async with session_factory() as session:
            job = await session.get(DocumentProcessingJob, job_id)
            if job:
                job.status = JobStatus.FAILED
                job.current_stage = "Failed"
                job.stage_progress_json = stage_progress
                job.error_message = str(exc)[:2000]
                job.completed_at_utc = _utcnow()
                await session.commit()

        async with session_factory() as session:
            doc = await session.get(KnowledgeDocument, doc_id)
            if doc:
                doc.status = IngestStatus.FAILED
                doc.ingest_error = str(exc)[:2000]
                await session.commit()

        return False


async def _update_job_progress(
    session_factory,
    job_id: int | None,
    current_stage: str,
    stage_progress: list,
) -> None:
    if job_id is None:
        return
    try:
        from sqlalchemy import update
        async with session_factory() as session:
            await session.execute(
                update(DocumentProcessingJob)
                .where(DocumentProcessingJob.id == job_id)
                .values(
                    current_stage=current_stage,
                    stage_progress_json=json.loads(json.dumps(stage_progress)),
                )
            )
            await session.commit()
    except Exception as exc:
        logger.warning(f"Failed to update job progress for job {job_id}: {exc}")
