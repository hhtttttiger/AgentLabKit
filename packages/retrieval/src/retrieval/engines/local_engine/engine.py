import os
from loguru import logger
from typing import Optional, List

from retrieval.engines.local_engine.context import PipelineContext
from retrieval.engines.local_engine.steps.base_step import PipelineStep
from retrieval.engines.local_engine.steps.document_loader_step.document_loader_step import DocumentLoaderStep
from retrieval.engines.local_engine.steps.document_splitter_step import DocumentSplitterStep
from retrieval.engines.local_engine.steps.tokenizer_step import TokenizerStep
from retrieval.engines.local_engine.steps.terminology_step import TerminologyStep
from retrieval.engines.local_engine.steps.index_builder_step import IndexBuilderStep
from retrieval.engines.local_engine.steps.graph_builder_step import GraphBuilderStep
from retrieval.engines.local_engine.steps.gc_step import GCStep
from retrieval.model import (
    SegmentInfo,
    SearchResult,
    GraphSearchResult,
    GraphSummary,
    GraphNode,
    GraphEdge,
    GraphSubgraph,
)
from retrieval.engines.local_engine.document_loaders.base import FileInfo
from retrieval.interface import BaseRagEngine, BaseGraphRagEngine
from retrieval.engines.local_engine.retrievers.hybrid import HybridRetriever
from retrieval.engines.local_engine.graph.repository.factory import create_graph_repository
from retrieval.engines.local_engine.graph.services.query import GraphQueryService
from retrieval.engines.local_engine.graph.services.retriever import GraphRetriever

class LocalRagEngine(BaseRagEngine, BaseGraphRagEngine):
    """
    本地 RAG 引擎实现
    使用本地管道处理文档：加载 -> 分割 -> 清理 -> 索引
    提供本地多路召回能力

    内部委托给 DocumentProcessor 处理文档，保持外部 API 向后兼容。
    """
    def __init__(self, file_path: str, segment_info: Optional[SegmentInfo] = None):
        super().__init__(file_path, segment_info)
        self.context = PipelineContext()
        self.graph_query_service: Optional[GraphQueryService] = None
        self.graph_retriever: Optional[GraphRetriever] = None
        self._init_context()
        self.retriever = HybridRetriever(self.segment_info)

    def _init_context(self):
        """Initialize context with default settings"""
        if self.segment_info is None:
            self.segment_info = SegmentInfo()

        self.context.segment_info = self.segment_info
        self.context.apply_defaults(self.context.segment_info.setting)

        file_name = os.path.basename(self.file_path)
        self.context.file_info = FileInfo(
            path=self.file_path,
            name=file_name
        )
        if self.context.graph_enabled:
            self.context.graph_repository = create_graph_repository(self.context.segment_info.setting.graph.storage)
            self.graph_query_service = GraphQueryService(self.context.graph_repository)
            self.graph_retriever = GraphRetriever(self.context.graph_repository)

    def search(self, query: str, top_k: int = 5, **kwargs) -> List[SearchResult]:
        """执行本地检索"""
        if not self.retriever:
            self.retriever = HybridRetriever(self.segment_info)
        self.retriever.sync_dataset(self.context.text_list, self.context.index_result)
        return self.retriever.search(query, top_k)

    def graph_search(self, query: str, top_k: int = 5, max_hops: int = 2, **kwargs) -> List[GraphSearchResult]:
        self._ensure_graph_ready()
        return self.graph_retriever.search(query, self.context.text_list, top_k=top_k, max_hops=max_hops)

    def get_graph_summary(self) -> GraphSummary:
        self._ensure_graph_ready()
        return self.graph_query_service.get_summary()

    def list_graph_nodes(self, label: str | None = None, limit: int = 100, **kwargs) -> List[GraphNode]:
        self._ensure_graph_ready()
        return self.graph_query_service.list_nodes(label=label, limit=limit)

    def list_graph_edges(self, relation: str | None = None, limit: int = 100, **kwargs) -> List[GraphEdge]:
        self._ensure_graph_ready()
        return self.graph_query_service.list_edges(relation=relation, limit=limit)

    def get_subgraph(self, node_ids: List[str], max_hops: int = 1, **kwargs) -> GraphSubgraph:
        self._ensure_graph_ready()
        return self.graph_query_service.get_subgraph(node_ids=node_ids, max_hops=max_hops)

    def activate(self) -> bool:
        """执行本地 RAG 流程"""
        steps: list[PipelineStep] = [
            DocumentLoaderStep(self.context),
            DocumentSplitterStep(self.context),
            TokenizerStep(self.context),
            TerminologyStep(self.context),
            GCStep(self.context),
            IndexBuilderStep(self.context),
            GraphBuilderStep(self.context),
        ]

        try:
            for step in steps:
                step.execute()
                if not self.context.success:
                    logger.error(f"Step {step.__class__.__name__} failed.")
                    break
        except Exception as e:
            self.context.success = False
            logger.exception(f"RAG Engine failed: {str(e)}")

        logger.info(f'Local RAG processing completed: {self.context.success}')
        return self.context.success

    def _ensure_graph_ready(self) -> None:
        if not self.context.graph_enabled:
            raise RuntimeError("GraphRAG is disabled for the current engine.")
        if self.context.graph_repository is None or self.graph_query_service is None or self.graph_retriever is None:
            raise RuntimeError("GraphRAG backend is not initialized.")
        if self.context.segment_info.status.graph.status != 1:
            raise RuntimeError("GraphRAG graph has not been built yet. Call activate() first.")
