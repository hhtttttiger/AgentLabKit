from typing import Dict, List

from retrieval.engines.local_engine.graph.repository.base import BaseGraphRepository
from retrieval.model import GraphSearchResult, Segment


class GraphRetriever:
    """Graph-oriented retrieval built on top of the graph repository."""

    def __init__(self, repository: BaseGraphRepository):
        self.repository = repository

    def search(self, query: str, segments: List[Segment], top_k: int = 5, max_hops: int = 2) -> List[GraphSearchResult]:
        matches = self.repository.search_nodes(query, limit=top_k)
        segment_map: Dict[int, Segment] = {segment.id: segment for segment in segments}
        results: List[GraphSearchResult] = []

        for rank, node in enumerate(matches, start=1):
            subgraph = self.repository.get_subgraph([node.id], max_hops=max_hops)
            segment_id = node.segment_ids[0] if node.segment_ids else None
            segment = segment_map.get(segment_id) if segment_id is not None else None
            result_text = segment.text if segment else ""
            source = ""
            if segment is not None:
                source = segment.metadata.get("source", "") or segment.metadata.get("file_name", "")

            results.append(
                GraphSearchResult(
                    id=node.id,
                    text=result_text,
                    score=max(0.0, 1.0 - (rank - 1) * 0.1),
                    source=source,
                    segment_id=segment_id,
                    nodes=subgraph.nodes,
                    edges=subgraph.edges,
                    paths=[[node.id]],
                    metadata={
                        "matched_node": node.name,
                        "max_hops": max_hops,
                    },
                )
            )

        return results
