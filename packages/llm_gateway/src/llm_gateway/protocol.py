"""Gateway protocol — structural interface for LLM gateway implementations.

Consumers should depend on this protocol rather than the concrete
:class:`GatewayService` to allow swapping the underlying implementation
(e.g. remote gateway client, test mock).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from .models import (
    EmbeddingGenerateRequest,
    EmbeddingGenerateResponse,
    TextGenerateRequest,
    TextGenerateResponse,
    TextStreamEvent,
)


class GatewayProtocol(Protocol):
    """Structural protocol for LLM gateway implementations.

    Any class that implements these three methods with compatible signatures
    satisfies this protocol — no inheritance required (Python structural
    subtyping).
    """

    async def generate_text(self, request: TextGenerateRequest) -> TextGenerateResponse:
        """Generate a text response (non-streaming)."""
        ...

    def generate_text_stream(self, request: TextGenerateRequest) -> AsyncIterator[TextStreamEvent]:
        """Generate a text response as a stream of events."""
        ...

    async def generate_embedding(self, request: EmbeddingGenerateRequest) -> EmbeddingGenerateResponse:
        """Generate an embedding vector."""
        ...
