from typing import List, Tuple

from retrieval.model import GraphEdge, GraphNode, Segment
from retrieval.engines.local_engine.graph.extractors.base import BaseGraphExtractor


class LlmGraphExtractor(BaseGraphExtractor):
    """
    Placeholder for future LLM enrichment.
    It intentionally returns no result in the template baseline.
    """

    def extract(self, segment: Segment) -> Tuple[List[GraphNode], List[GraphEdge]]:
        return [], []
