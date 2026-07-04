from collections import Counter, defaultdict, deque
from typing import Dict, List

from retrieval.model import GraphEdge, GraphNode, GraphSubgraph, GraphSummary
from retrieval.engines.local_engine.graph.repository.base import BaseGraphRepository


class InMemoryGraphRepository(BaseGraphRepository):
    """Test-friendly graph repository."""

    def __init__(self, graph_name: str = "rag_graph"):
        self.graph_name = graph_name
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[str, GraphEdge] = {}

    def ensure_graph(self) -> None:
        return None

    def upsert_nodes(self, nodes: List[GraphNode]) -> None:
        for node in nodes:
            existing = self.nodes.get(node.id)
            if existing is None:
                self.nodes[node.id] = node
                continue

            existing.segment_ids = sorted(set(existing.segment_ids + node.segment_ids))
            existing.properties.update(node.properties)
            if not existing.name:
                existing.name = node.name
            if not existing.label:
                existing.label = node.label

    def upsert_edges(self, edges: List[GraphEdge]) -> None:
        for edge in edges:
            existing = self.edges.get(edge.id)
            if existing is None:
                self.edges[edge.id] = edge
                continue

            existing.segment_ids = sorted(set(existing.segment_ids + edge.segment_ids))
            existing.properties.update(edge.properties)

    def get_summary(self) -> GraphSummary:
        labels = Counter(node.label for node in self.nodes.values())
        relations = Counter(edge.relation for edge in self.edges.values())
        return GraphSummary(
            graph_name=self.graph_name,
            backend="memory",
            node_count=len(self.nodes),
            edge_count=len(self.edges),
            labels=dict(labels),
            relations=dict(relations),
        )

    def list_nodes(self, label: str | None = None, limit: int = 100) -> List[GraphNode]:
        nodes = list(self.nodes.values())
        if label:
            nodes = [node for node in nodes if node.label == label]
        return nodes[:limit]

    def list_edges(self, relation: str | None = None, limit: int = 100) -> List[GraphEdge]:
        edges = list(self.edges.values())
        if relation:
            edges = [edge for edge in edges if edge.relation == relation]
        return edges[:limit]

    def get_subgraph(self, node_ids: List[str], max_hops: int = 1) -> GraphSubgraph:
        adjacency = defaultdict(list)
        for edge in self.edges.values():
            adjacency[edge.source_id].append(edge)
            adjacency[edge.target_id].append(edge)

        visited = set(node_ids)
        queue = deque((node_id, 0) for node_id in node_ids if node_id in self.nodes)
        collected_edges: Dict[str, GraphEdge] = {}
        while queue:
            node_id, depth = queue.popleft()
            if depth >= max_hops:
                continue
            for edge in adjacency.get(node_id, []):
                collected_edges[edge.id] = edge
                neighbor_id = edge.target_id if edge.source_id == node_id else edge.source_id
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, depth + 1))

        return GraphSubgraph(
            nodes=[self.nodes[node_id] for node_id in visited if node_id in self.nodes],
            edges=list(collected_edges.values()),
        )

    def search_nodes(self, query: str, limit: int = 10) -> List[GraphNode]:
        lowered = query.lower().strip()
        if not lowered:
            return []
        matches = [
            node for node in self.nodes.values()
            if lowered in node.name.lower() or lowered in node.label.lower()
        ]
        return matches[:limit]
