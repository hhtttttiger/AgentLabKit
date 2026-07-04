import hashlib
import re
from typing import Dict, List, Set, Tuple

from retrieval.model import GraphNode, GraphEdge, Segment
from retrieval.engines.local_engine.graph.extractors.base import BaseGraphExtractor


class RuleGraphExtractor(BaseGraphExtractor):
    """A lightweight rule-based extractor that is stable in tests."""

    RELATION_PATTERNS = [
        # English patterns
        ("uses", r"(?P<source>[A-Z][A-Za-z0-9_+\- ]{0,40}?)\s+uses\s+(?P<target>[A-Z][A-Za-z0-9_+\- ]{0,40})"),
        ("contains", r"(?P<source>[A-Z][A-Za-z0-9_+\- ]{0,40}?)\s+contains\s+(?P<target>[A-Z][A-Za-z0-9_+\- ]{0,40})"),
        ("depends_on", r"(?P<source>[A-Z][A-Za-z0-9_+\- ]{0,40}?)\s+depends on\s+(?P<target>[A-Z][A-Za-z0-9_+\- ]{0,40})"),
        ("works_with", r"(?P<source>[A-Z][A-Za-z0-9_+\- ]{0,40}?)\s+works with\s+(?P<target>[A-Z][A-Za-z0-9_+\- ]{0,40})"),
        ("references", r"(?P<source>[A-Z][A-Za-z0-9_+\- ]{0,40}?)\s+references\s+(?P<target>[A-Z][A-Za-z0-9_+\- ]{0,40})"),
        ("part_of", r"(?P<target>[A-Z][A-Za-z0-9_+\- ]{0,40}?)\s+includes\s+(?P<source>[A-Z][A-Za-z0-9_+\- ]{0,40})"),
        # Chinese patterns
        ("使用", r"(?P<source>[一-鿿]{2,10})\s*使用\s*(?P<target>[一-鿿]{2,10})"),
        ("包含", r"(?P<source>[一-鿿]{2,10})\s*包含\s*(?P<target>[一-鿿]{2,10})"),
        ("依赖于", r"(?P<source>[一-鿿]{2,10})\s*依赖于?\s*(?P<target>[一-鿿]{2,10})"),
        ("属于", r"(?P<source>[一-鿿]{2,10})\s*属于\s*(?P<target>[一-鿿]{2,10})"),
        ("调用", r"(?P<source>[一-鿿]{2,10})\s*调用\s*(?P<target>[一-鿿]{2,10})"),
    ]
    # English capitalized entities + Chinese entities (2-10 CJK chars)
    ENTITY_PATTERN = re.compile(
        r"\b([A-Z][A-Za-z0-9_+\-]*(?:\s+[A-Z][A-Za-z0-9_+\-]*){0,2})\b"
        r"|([一-鿿]{2,10})"
    )

    def __init__(self, max_triplets_per_segment: int = 20, confidence: float = 0.7):
        self.max_triplets_per_segment = max_triplets_per_segment
        self.confidence = confidence

    def extract(self, segment: Segment) -> Tuple[List[GraphNode], List[GraphEdge]]:
        nodes: Dict[str, GraphNode] = {}
        edges: Dict[str, GraphEdge] = {}
        seen_entities: Set[str] = set()

        for relation, pattern in self.RELATION_PATTERNS:
            for match in re.finditer(pattern, segment.text):
                source_name = self._normalize_name(match.group("source"))
                target_name = self._normalize_name(match.group("target"))
                if not source_name or not target_name:
                    continue

                source_node = self._build_node(source_name, segment)
                target_node = self._build_node(target_name, segment)
                nodes[source_node.id] = source_node
                nodes[target_node.id] = target_node
                seen_entities.add(source_name.lower())
                seen_entities.add(target_name.lower())

                edge = self._build_edge(source_node.id, target_node.id, relation, segment)
                edges[edge.id] = edge
                if len(edges) >= self.max_triplets_per_segment:
                    return list(nodes.values()), list(edges.values())

        for match in self.ENTITY_PATTERN.finditer(segment.text):
            entity = match.group(1) or match.group(2) or ""
            normalized = self._normalize_name(entity)
            if not normalized or normalized.lower() in seen_entities:
                continue
            node = self._build_node(normalized, segment)
            nodes[node.id] = node

        return list(nodes.values()), list(edges.values())

    def _build_node(self, name: str, segment: Segment) -> GraphNode:
        node_id = self._entity_id(name)
        return GraphNode(
            id=node_id,
            name=name,
            label="Entity",
            properties={
                "name": name,
                "extractor": "rule",
                "confidence": self.confidence,
            },
            segment_ids=[segment.id],
        )

    def _build_edge(self, source_id: str, target_id: str, relation: str, segment: Segment) -> GraphEdge:
        edge_id = hashlib.sha1(f"{source_id}:{relation}:{target_id}".encode("utf-8")).hexdigest()
        return GraphEdge(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            properties={
                "extractor": "rule",
                "confidence": self.confidence,
            },
            segment_ids=[segment.id],
        )

    def _entity_id(self, name: str) -> str:
        return hashlib.sha1(name.lower().encode("utf-8")).hexdigest()

    def _normalize_name(self, value: str) -> str:
        normalized = " ".join(value.strip().split())
        return normalized.strip(".,;:()[]{}")
