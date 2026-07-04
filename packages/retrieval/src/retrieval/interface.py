from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, List

from pydantic import BaseModel, Field

from retrieval.model import (
    SegmentInfo,
    SegmentSetting,
    DocumentSource,
    SearchResult,
    GraphSearchResult,
    GraphSummary,
    GraphNode,
    GraphEdge,
    GraphSubgraph,
    Segment,
    Index,
)

class BaseRagEngine(ABC):
    """
    RAG 引擎抽象基类
    定义所有 RAG 引擎必须实现的接口
    """
    
    def __init__(self, file_path: str, segment_info: Optional[SegmentInfo] = None):
        self.file_path = file_path
        self.segment_info = segment_info

    @abstractmethod
    def activate(self) -> bool:
        """
        激活 RAG 处理流程
        :return: 处理是否成功
        """
        pass

    @abstractmethod
    def search(self, query: str, top_k: int = 5, **kwargs) -> List[SearchResult]:
        """
        执行检索/召回
        :param query: 搜索查询词
        :param top_k: 返回的最相关结果数量
        :return: 检索结果列表
        """
        pass

class BaseGraphRagEngine(ABC):
    """
    GraphRAG 扩展接口
    """

    @abstractmethod
    def graph_search(self, query: str, top_k: int = 5, max_hops: int = 2, **kwargs) -> List[GraphSearchResult]:
        """执行图谱检索"""
        pass

    @abstractmethod
    def get_graph_summary(self) -> GraphSummary:
        """获取图谱摘要"""
        pass

    @abstractmethod
    def list_graph_nodes(self, label: str | None = None, limit: int = 100, **kwargs) -> List[GraphNode]:
        """列出图节点"""
        pass

    @abstractmethod
    def list_graph_edges(self, relation: str | None = None, limit: int = 100, **kwargs) -> List[GraphEdge]:
        """列出图边"""
        pass

    @abstractmethod
    def get_subgraph(self, node_ids: List[str], max_hops: int = 1, **kwargs) -> GraphSubgraph:
        """获取子图"""
        pass


# --- 知识库级操作接口 ---

class ProcessingResult(BaseModel):
    """文档处理结果 — 可序列化、可持久化"""
    segments: List[Segment] = Field(default_factory=list)
    indexes: List[Index] = Field(default_factory=list)
    graph_nodes: List[GraphNode] = Field(default_factory=list)
    graph_edges: List[GraphEdge] = Field(default_factory=list)
    success: bool = True
    error_message: str = ""


class BaseRetrievalService(ABC):
    """知识库级操作抽象基类

    索引文档、跨文档检索、删除文档。
    由 backend 中的 KnowledgeRetrievalService 实现。
    """

    @abstractmethod
    async def aindex_document(
        self,
        kb_id: str,
        doc_id: str,
        source: DocumentSource,
        setting: Optional[SegmentSetting] = None,
    ) -> ProcessingResult:
        """处理并索引单个文档到知识库"""
        ...

    @abstractmethod
    async def aremove_document(self, kb_id: str, doc_id: str) -> bool:
        """从知识库中移除文档的所有分段和索引"""
        ...

    @abstractmethod
    async def asearch(self, kb_id: str, query: str, top_k: int = 5, **kwargs) -> List[SearchResult]:
        """在知识库中跨文档检索"""
        ...
