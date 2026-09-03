"""Runtime-owned retrieval observation seam."""
from __future__ import annotations

import time
from collections.abc import Sequence
from contextlib import asynccontextmanager
from typing import AsyncIterator
from uuid import uuid4

from ..contracts.models import KnowledgeChunk
from ..events_v2 import RetrievalCompleted, RetrievalFailed, RetrievalResultRef, RetrievalStarted
from ..tools.contracts import RetrievalObservation, RetrievalObserver
from .loop import SemanticEventSink, _SpanContext

_RESULT_CAP = 10
_PREVIEW_LIMIT = 400


class RuntimeRetrievalObserver(RetrievalObserver):
    """Allocates nested retrieval spans without exposing runtime identity to tools."""

    def __init__(self, emit: SemanticEventSink, span_context: _SpanContext) -> None:
        self._emit = emit
        self._span_context = span_context

    @asynccontextmanager
    async def observe(
        self, *, query: str, source: str, knowledge_base_ids: Sequence[str] = (),
        top_k: int | None = None, search_mode: str | None = None,
    ) -> AsyncIterator[RetrievalObservation]:
        span_id = uuid4().hex[:16]
        parent_span_id = self._span_context.current_span_id
        self._span_context.push(span_id)
        observation = _RuntimeRetrievalObservation()
        started = time.perf_counter()
        await self._emit(RetrievalStarted(
            query=query, source=source, knowledge_base_ids=tuple(knowledge_base_ids),
            top_k=top_k, search_mode=search_mode, span_id=span_id,
            parent_span_id=parent_span_id,
        ))
        try:
            yield observation
        except BaseException as exc:
            await self._emit(RetrievalFailed(
                error_message=str(exc) or exc.__class__.__name__, span_id=span_id,
                parent_span_id=parent_span_id,
            ))
            raise
        else:
            await self._emit(RetrievalCompleted(
                result_count=observation.result_count,
                duration_ms=int((time.perf_counter() - started) * 1000),
                results=tuple(observation.refs), span_id=span_id,
                parent_span_id=parent_span_id,
            ))
        finally:
            self._span_context.pop()


class _RuntimeRetrievalObservation(RetrievalObservation):
    def __init__(self) -> None:
        self.result_count = 0
        self.refs: list[RetrievalResultRef] = []

    def set_results(self, results: Sequence[KnowledgeChunk]) -> None:
        self.result_count = len(results)
        self.refs = [
            RetrievalResultRef(
                knowledge_base_id=chunk.knowledge_base_id,
                document_id=chunk.document_id,
                segment_id=chunk.segment_id,
                score=chunk.score,
                title=chunk.title,
                source=chunk.source,
                content_preview=chunk.content[:_PREVIEW_LIMIT] if chunk.content else None,
            )
            for chunk in results[:_RESULT_CAP]
        ]


__all__ = ["RuntimeRetrievalObserver"]
