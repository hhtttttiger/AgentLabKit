from typing import List

from retrieval.engines.local_engine.graph.extractors.base import BaseGraphExtractor
from retrieval.engines.local_engine.graph.repository.base import BaseGraphRepository
from retrieval.model import GraphBuildStatus, GraphNode, GraphEdge, GraphSummary, Segment


class GraphBuildService:
    """Coordinate extraction and repository writes."""

    def __init__(self, repository: BaseGraphRepository, status: GraphBuildStatus, graph_name: str):
        self.repository = repository
        self.status = status
        self.graph_name = graph_name

    def build(self, segments: List[Segment], extractor: BaseGraphExtractor, file_path: str, file_name: str) -> GraphSummary:
        self.repository.ensure_graph()
        all_nodes: List[GraphNode] = []
        all_edges: List[GraphEdge] = []

        for segment in segments:
            nodes, edges = extractor.extract(segment)
            for node in nodes:
                enriched_node = self._add_provenance_to_node(node, segment, file_path, file_name)
                all_nodes.append(enriched_node)
            for edge in edges:
                enriched_edge = self._add_provenance_to_edge(edge, segment, file_path, file_name)
                all_edges.append(enriched_edge)

        self.repository.upsert_nodes(all_nodes)
        self.repository.upsert_edges(all_edges)
        return self.repository.get_summary()

    def _add_provenance_to_node(self, node: GraphNode, segment: Segment, file_path: str, file_name: str) -> GraphNode:
        enriched = node.model_copy(deep=True)
        enriched.properties.update(self._build_provenance(segment, file_path, file_name))
        return enriched

    def _add_provenance_to_edge(self, edge: GraphEdge, segment: Segment, file_path: str, file_name: str) -> GraphEdge:
        enriched = edge.model_copy(deep=True)
        enriched.properties.update(self._build_provenance(segment, file_path, file_name))
        return enriched

    def _build_provenance(self, segment: Segment, file_path: str, file_name: str) -> dict:
        page_number = segment.metadata.get("page_number", 0)
        return {
            "segment_id": segment.id,
            "file_path": file_path,
            "file_name": file_name,
            "page_number": page_number,
        }
