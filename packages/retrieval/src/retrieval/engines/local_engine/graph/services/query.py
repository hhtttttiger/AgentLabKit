from typing import List

from retrieval.engines.local_engine.graph.repository.base import BaseGraphRepository
from retrieval.model import GraphEdge, GraphNode, GraphSubgraph, GraphSummary


class GraphQueryService:
    """Read-only graph inspection service."""

    def __init__(self, repository: BaseGraphRepository):
        self.repository = repository

    def get_summary(self) -> GraphSummary:
        return self.repository.get_summary()

    def list_nodes(self, label: str | None = None, limit: int = 100) -> List[GraphNode]:
        return self.repository.list_nodes(label=label, limit=limit)

    def list_edges(self, relation: str | None = None, limit: int = 100) -> List[GraphEdge]:
        return self.repository.list_edges(relation=relation, limit=limit)

    def get_subgraph(self, node_ids: List[str], max_hops: int = 1) -> GraphSubgraph:
        return self.repository.get_subgraph(node_ids=node_ids, max_hops=max_hops)
