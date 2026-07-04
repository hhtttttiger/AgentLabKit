from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import math
import re
from typing import List

from retrieval.model import Index, SearchResult, Segment, SegmentInfo

from .base import BaseRetriever

_TOKEN_PATTERN = re.compile(r"[a-z0-9_\-\u4e00-\u9fff]+", re.IGNORECASE)
_SEARCHABLE_INDEX_TYPES = {"full_text", "embedding"}


def _normalize_text(value: str) -> str:
    return " ".join(_TOKEN_PATTERN.findall((value or "").lower()))


def _tokenize(value: str) -> list[str]:
    return _TOKEN_PATTERN.findall((value or "").lower())


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


@dataclass(slots=True)
class _SegmentSnapshot:
    segment: Segment
    searchable_text: str
    searchable_tokens: frozenset[str]
    source: str


class HybridRetriever(BaseRetriever):
    """In-memory hybrid retriever using segment text plus built indexes."""

    def __init__(self, segment_info: SegmentInfo):
        super().__init__(segment_info)
        self._segments: list[_SegmentSnapshot] = []
        self._indexes_by_segment: dict[int, list[Index]] = defaultdict(list)
        # 可配置的评分权重，默认 0.7/0.3
        provider_config = segment_info.setting.provider_config
        self._keyword_weight: float = provider_config.get("keyword_weight", 0.7)
        self._index_weight: float = provider_config.get("index_weight", 0.3)

    def sync_dataset(self, segments: List[Segment], indexes: List[Index]) -> None:
        self._segments = [
            _SegmentSnapshot(
                segment=segment,
                searchable_text=_normalize_text(segment.text),
                searchable_tokens=frozenset(_tokenize(segment.text)),
                source=self._resolve_source(segment),
            )
            for segment in segments
            if segment.text.strip()
        ]
        self._indexes_by_segment = defaultdict(list)
        for index in indexes:
            self._indexes_by_segment[index.segment_id].append(index)

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        normalized_query = query.strip()
        if not normalized_query or top_k <= 0 or not self._segments:
            return []

        query_text = _normalize_text(normalized_query)
        query_tokens = frozenset(_tokenize(normalized_query))
        if not query_text or not query_tokens:
            return []

        ranked: list[tuple[float, SearchResult]] = []
        for snapshot in self._segments:
            score = self._score_segment(snapshot, query_text, query_tokens)
            if score <= 0:
                continue

            ranked.append(
                (
                    score,
                    SearchResult(
                        id=str(snapshot.segment.id),
                        text=snapshot.segment.text,
                        source=snapshot.source,
                        score=round(score, 6),
                        metadata={
                            key: str(value)
                            for key, value in snapshot.segment.metadata.items()
                            if value is not None
                        },
                    ),
                )
            )

        ranked.sort(
            key=lambda item: (
                -item[0],
                item[1].source,
                item[1].id,
            )
        )
        return [result for _, result in ranked[:top_k]]

    def _score_segment(
        self,
        snapshot: _SegmentSnapshot,
        query_text: str,
        query_tokens: frozenset[str],
    ) -> float:
        keyword_score = self._keyword_score(snapshot, query_text, query_tokens)
        index_score = self._index_score(snapshot.segment.id, query_text, query_tokens)
        if keyword_score <= 0 and index_score <= 0:
            return 0.0
        return round((keyword_score * self._keyword_weight) + (index_score * self._index_weight), 6)

    def _keyword_score(
        self,
        snapshot: _SegmentSnapshot,
        query_text: str,
        query_tokens: frozenset[str],
    ) -> float:
        overlap = len(query_tokens & snapshot.searchable_tokens)
        if overlap == 0:
            return 0.0

        coverage = _safe_divide(overlap, len(query_tokens))
        density = _safe_divide(overlap, math.sqrt(len(snapshot.searchable_tokens) or 1))
        exact_phrase_bonus = 0.35 if query_text in snapshot.searchable_text else 0.0
        prefix_bonus = 0.1 if snapshot.searchable_text.startswith(query_text) else 0.0
        return coverage + density + exact_phrase_bonus + prefix_bonus

    def _index_score(
        self,
        segment_id: int,
        query_text: str,
        query_tokens: frozenset[str],
    ) -> float:
        best_score = 0.0
        for index in self._indexes_by_segment.get(segment_id, []):
            if index.type.lower() not in _SEARCHABLE_INDEX_TYPES:
                continue
            index_text = _normalize_text(index.index or index.context)
            if not index_text:
                continue
            index_tokens = frozenset(_tokenize(index.index or index.context))
            overlap = len(query_tokens & index_tokens)
            if overlap == 0:
                continue
            coverage = _safe_divide(overlap, len(query_tokens))
            exact_phrase_bonus = 0.25 if query_text in index_text else 0.0
            best_score = max(best_score, coverage + exact_phrase_bonus)
        return best_score

    def _resolve_source(self, segment: Segment) -> str:
        source = segment.metadata.get("source") or segment.metadata.get("file_name")
        return str(source or "")
