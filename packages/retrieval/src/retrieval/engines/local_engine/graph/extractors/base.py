from abc import ABC, abstractmethod
from typing import List, Tuple

from retrieval.model import GraphNode, GraphEdge, Segment


class BaseGraphExtractor(ABC):
    """Graph extractor contract."""

    @abstractmethod
    def extract(self, segment: Segment) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """Extract nodes and edges from a segment."""
        pass
