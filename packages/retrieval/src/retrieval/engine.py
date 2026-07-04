from typing import Optional, List
from retrieval.model import (
    SegmentInfo,
    SearchResult,
    GraphSearchResult,
    GraphSummary,
    GraphNode,
    GraphEdge,
    GraphSubgraph,
)
from retrieval.interface import BaseRagEngine, BaseGraphRagEngine
from retrieval.engines.local_engine.engine import LocalRagEngine

class RagEngine:
    """
    RAG 引擎门面类 (Facade)

    根据配置（segment_info.setting.provider）动态分发请求到
    LocalRagEngine。
    """
    def __init__(self, file_path: str, segment_info: Optional[SegmentInfo] = None):
        self.file_path = file_path
        # 如果未提供 info，则初始化默认值以便读取配置
        self.segment_info = segment_info or SegmentInfo()
        
        # 根据配置选择实现
        self.engine: BaseRagEngine = self._create_engine()

    def _create_engine(self) -> BaseRagEngine:
        """工厂方法：根据配置创建具体的引擎实例"""
        provider = self.segment_info.setting.provider

        if provider == "local":
            return LocalRagEngine(self.file_path, self.segment_info)
        else:
            return LocalRagEngine(self.file_path, self.segment_info)

    def activate(self) -> bool:
        """代理执行激活操作"""
        return self.engine.activate()

    def search(self, query: str, top_k: int = 5, **kwargs) -> List[SearchResult]:
        """代理执行检索操作"""
        return self.engine.search(query, top_k, **kwargs)

    def graph_search(self, query: str, top_k: int = 5, max_hops: int = 2, **kwargs) -> List[GraphSearchResult]:
        """代理执行图谱检索"""
        graph_engine = self._require_graph_engine()
        return graph_engine.graph_search(query, top_k=top_k, max_hops=max_hops, **kwargs)

    def get_graph_summary(self) -> GraphSummary:
        """代理获取图谱摘要"""
        graph_engine = self._require_graph_engine()
        return graph_engine.get_graph_summary()

    def list_graph_nodes(self, label: str | None = None, limit: int = 100, **kwargs) -> List[GraphNode]:
        """代理列出图节点"""
        graph_engine = self._require_graph_engine()
        return graph_engine.list_graph_nodes(label=label, limit=limit, **kwargs)

    def list_graph_edges(self, relation: str | None = None, limit: int = 100, **kwargs) -> List[GraphEdge]:
        """代理列出图边"""
        graph_engine = self._require_graph_engine()
        return graph_engine.list_graph_edges(relation=relation, limit=limit, **kwargs)

    def get_subgraph(self, node_ids: List[str], max_hops: int = 1, **kwargs) -> GraphSubgraph:
        """代理获取子图"""
        graph_engine = self._require_graph_engine()
        return graph_engine.get_subgraph(node_ids=node_ids, max_hops=max_hops, **kwargs)

    def _require_graph_engine(self) -> BaseGraphRagEngine:
        if not isinstance(self.engine, BaseGraphRagEngine):
            raise NotImplementedError("GraphRAG is not supported by the current provider.")
        return self.engine
