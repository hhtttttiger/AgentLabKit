from abc import ABC, abstractmethod
from typing import List

from retrieval.model import GraphEdge, GraphNode, GraphSubgraph, GraphSummary


class BaseGraphRepository(ABC):
    """Storage contract for GraphRAG backends."""

    @abstractmethod
    def ensure_graph(self) -> None:
        pass

    @abstractmethod
    def upsert_nodes(self, nodes: List[GraphNode]) -> None:
        pass

    @abstractmethod
    def upsert_edges(self, edges: List[GraphEdge]) -> None:
        pass

    @abstractmethod
    def get_summary(self) -> GraphSummary:
        pass

    @abstractmethod
    def list_nodes(self, label: str | None = None, limit: int = 100) -> List[GraphNode]:
        pass

    @abstractmethod
    def list_edges(self, relation: str | None = None, limit: int = 100) -> List[GraphEdge]:
        pass

    @abstractmethod
    def get_subgraph(self, node_ids: List[str], max_hops: int = 1) -> GraphSubgraph:
        pass

    @abstractmethod
    def search_nodes(self, query: str, limit: int = 10) -> List[GraphNode]:
        pass
