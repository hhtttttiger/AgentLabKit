"""DocumentProcessor — 无状态文档处理器

从 LocalRagEngine.activate() 中提取的独立处理逻辑。
内部创建 PipelineContext，跑完 pipeline 后返回 ProcessingResult，不持有状态。

使用方式::

    processor = DocumentProcessor(embedding_provider=provider)
    result = processor.process(source, setting)
    # result.segments / result.indexes / result.graph_nodes / result.graph_edges
"""
from __future__ import annotations

import asyncio
import os
import tempfile
from loguru import logger
from typing import TYPE_CHECKING, Callable, Optional

from retrieval.interface import ProcessingResult
from retrieval.model import (
    DocumentSource,
    Segment,
    Index,
    SegmentInfo,
    SegmentSetting,
    GraphNode,
    GraphEdge,
)
from retrieval.engines.local_engine.context import PipelineContext
from retrieval.engines.local_engine.document_loaders.base import Document, FileInfo
from retrieval.engines.local_engine.steps.base_step import PipelineStep
from retrieval.engines.local_engine.steps.document_loader_step.document_loader_step import DocumentLoaderStep
from retrieval.engines.local_engine.steps.document_splitter_step import DocumentSplitterStep
from retrieval.engines.local_engine.steps.tokenizer_step import TokenizerStep
from retrieval.engines.local_engine.steps.terminology_step import TerminologyStep
from retrieval.engines.local_engine.steps.gc_step import GCStep
from retrieval.engines.local_engine.steps.index_builder_step import IndexBuilderStep
from retrieval.engines.local_engine.steps.graph_builder_step import GraphBuilderStep

if TYPE_CHECKING:
    from retrieval.providers.embedding import BaseEmbeddingProvider

# Callback signature: (step_name, step_index, total_steps, status)
# status is one of: "running", "done", "failed"
StepProgressCallback = Callable[[str, int, int, str], None]


class DocumentProcessor:
    """无状态文档处理器：DocumentSource → ProcessingResult

    每次调用 process() / aprocess() 都创建新的 PipelineContext，
    处理完成后返回结果，不保留任何中间状态。
    """

    def __init__(
        self,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
        on_step_change: Optional[StepProgressCallback] = None,
    ):
        self._embedding_provider = embedding_provider
        self._on_step_change = on_step_change

    def process(self, source: DocumentSource, setting: SegmentSetting) -> ProcessingResult:
        """同步处理文档"""
        context = self._build_context(source, setting)
        tmp_path = context.file_info.file_path if (source.content is not None and not source.file_path) else None
        steps = self._build_steps(context)
        total = len(steps)
        try:
            for i, step in enumerate(steps):
                if self._on_step_change:
                    self._on_step_change(step.name, i, total, "running")
                step.execute()
                if not context.success:
                    if self._on_step_change:
                        self._on_step_change(step.name, i, total, "failed")
                    logger.error(f"Step {step.__class__.__name__} failed.")
                    break
                if self._on_step_change:
                    self._on_step_change(step.name, i, total, "done")
        except Exception as e:
            context.success = False
            logger.exception(f"DocumentProcessor failed: {e}")
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        return self._build_result(context)

    async def aprocess(self, source: DocumentSource, setting: SegmentSetting) -> ProcessingResult:
        """异步处理文档。

        当有进度回调时，使用 run_in_executor 在线程池中执行同步 pipeline，
        这样回调中的 create_task 可以被事件循环调度，实现中间状态实时写入 DB。
        """
        if self._on_step_change:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self.process, source, setting)
        return self.process(source, setting)

    # --- 内部方法 ---

    def _build_context(self, source: DocumentSource, setting: SegmentSetting) -> PipelineContext:
        """根据 DocumentSource 构建 PipelineContext"""
        ctx = PipelineContext()
        ctx.segment_info = SegmentInfo(setting=setting)
        ctx.apply_defaults(setting)

        # 解析文件信息
        file_path = source.file_path or ""
        file_name = source.file_name or ""

        # 如果有 bytes 内容但没有 file_path，写入临时文件以便 loader 读取
        if source.content is not None and not file_path:
            suffix = os.path.splitext(file_name)[1] if file_name else ""
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            try:
                tmp.write(source.content)
                tmp.close()
                file_path = tmp.name
            except Exception:
                try:
                    os.unlink(tmp.name)
                except OSError:
                    pass
                raise

        ctx.file_info = FileInfo(path=file_path, name=file_name)

        return ctx

    def _build_steps(self, context: PipelineContext) -> list[PipelineStep]:
        """构建处理管道步骤"""
        steps: list[PipelineStep] = [
            DocumentLoaderStep(context),
            DocumentSplitterStep(context),
            TokenizerStep(context),
            TerminologyStep(context),
            GCStep(context),
            IndexBuilderStep(context),
            GraphBuilderStep(context),
        ]
        return steps

    def _build_result(self, context: PipelineContext) -> ProcessingResult:
        """从 PipelineContext 提取处理结果"""
        return ProcessingResult(
            segments=list(context.text_list),
            indexes=list(context.index_result),
            graph_nodes=[],  # graph 数据通过 context.graph_repository 获取
            graph_edges=[],
            success=context.success,
            error_message=context.segment_info.errorMessage if context.segment_info else "",
        )
