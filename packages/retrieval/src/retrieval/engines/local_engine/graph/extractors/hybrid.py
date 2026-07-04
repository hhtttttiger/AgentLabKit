from typing import List, Tuple

from retrieval.model import GraphEdge, GraphNode, Segment
from retrieval.engines.local_engine.graph.extractors.base import BaseGraphExtractor
from retrieval.engines.local_engine.graph.extractors.llm import LlmGraphExtractor
from retrieval.engines.local_engine.graph.extractors.rule_based import RuleGraphExtractor


class HybridGraphExtractor(BaseGraphExtractor):
    """Compose rule-based extraction with optional LLM enrichment."""

    def __init__(self, enable_llm_enrichment: bool = False, max_triplets_per_segment: int = 20):
        self.rule_extractor = RuleGraphExtractor(max_triplets_per_segment=max_triplets_per_segment)
        self.llm_extractor = LlmGraphExtractor() if enable_llm_enrichment else None

    def extract(self, segment: Segment) -> Tuple[List[GraphNode], List[GraphEdge]]:
        nodes, edges = self.rule_extractor.extract(segment)
        if self.llm_extractor is None:
            return nodes, edges

        llm_nodes, llm_edges = self.llm_extractor.extract(segment)
        merged_nodes = {node.id: node for node in nodes}
        merged_edges = {edge.id: edge for edge in edges}
        for node in llm_nodes:
            merged_nodes[node.id] = node
        for edge in llm_edges:
            merged_edges[edge.id] = edge
        return list(merged_nodes.values()), list(merged_edges.values())
