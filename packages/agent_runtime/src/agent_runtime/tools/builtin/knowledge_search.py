"""Built-in knowledge_search tool.

Migrated from :mod:`agent_runtime.tools.registry` into the built-in package
so it can be registered like any other tool via :class:`DynamicToolRegistry`.

The :class:`KnowledgeSearchTool` wraps a :class:`KnowledgeProvider` — the
same protocol that the legacy registry used — preserving full backward
compatibility.
"""

from __future__ import annotations

import inspect
from typing import Any

from ..contracts import ToolExecutionContext, ToolResult, ToolSpec
from ...contracts.models import KnowledgeChunk


# ---------------------------------------------------------------------------
# Spec (class-level constant, shared across all instances)
# ---------------------------------------------------------------------------

_SPEC = ToolSpec(
    name="knowledge_search",
    description=(
        "Search the knowledge base for grounded support information. "
        "Use this to look up product details, policies, or any factual "
        "information before answering the customer."
    ),
    parameters_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query string.",
            },
            "top_k": {
                "type": "integer",
                "minimum": 1,
                "description": "Maximum number of results to return (default: 5).",
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    },
    returns_description="Numbered list of knowledge chunks matching the query.",
    tags=frozenset({"rag", "read_only"}),
    timeout_seconds=10.0,
    max_retries=1,
    is_idempotent=True,
)


# ---------------------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------------------


class KnowledgeSearchTool:
    """Wraps a :class:`KnowledgeProvider` as a registered tool handler.

    Args:
        knowledge_provider: Any object implementing the ``search(query, top_k)``
            method (sync or async).  Uses :class:`NullKnowledgeProvider`
            behaviour when not provided.
        default_top_k: Fallback ``top_k`` value when the caller omits it.
    """

    spec: ToolSpec = _SPEC

    def __init__(
        self,
        knowledge_provider: Any = None,  # noqa: ANN401
        default_top_k: int = 5,
    ) -> None:
        self._provider = knowledge_provider
        self._default_top_k = default_top_k

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolResult:
        query: str = str(arguments.get("query", "")).strip()
        top_k: int = int(arguments.get("top_k", self._default_top_k))

        if not query:
            return ToolResult(
                output="No search query provided.",
                status="error",
                error_message="knowledge_search requires a non-empty 'query'.",
            )

        if self._provider is None:
            return ToolResult(
                output="Knowledge base is not configured for this runtime.",
                status="success",
            )

        try:
            if context.knowledge_bindings is not None:
                if not context.knowledge_bindings:
                    return ToolResult(
                        output=_stringify_chunks([]),
                        structured_data={
                            "chunks": [],
                            "knowledge_base_ids": [],
                            "binding_config_versions": [],
                        },
                        status="success",
                    )
                scoped_search = getattr(self._provider, "search_bound_knowledge_bases", None)
                if scoped_search is None:
                    return ToolResult(
                        output="",
                        status="error",
                        error_message="Knowledge provider does not support scoped knowledge bindings.",
                    )
                raw = scoped_search(
                    knowledge_bindings=list(context.knowledge_bindings),
                    query=query,
                    top_k=top_k,
                    agent_key=context.agent_key,
                    agent_version=context.agent_version,
                )
            else:
                raw = self._provider.search(query, top_k)
            if inspect.isawaitable(raw):
                chunks: list[KnowledgeChunk] = await raw
            else:
                chunks = raw
            return ToolResult(
                output=_stringify_chunks(chunks),
                structured_data={
                    "chunks": [c.model_dump() for c in chunks],
                    "knowledge_base_ids": [
                        binding.knowledge_base_id for binding in context.knowledge_bindings or ()
                    ],
                    "binding_config_versions": [
                        binding.config_version for binding in context.knowledge_bindings or ()
                    ],
                },
                status="success",
            )
        except Exception as exc:  # noqa: BLE001
            return ToolResult(
                output="",
                status="error",
                error_message=str(exc),
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stringify_chunks(chunks: list[KnowledgeChunk]) -> str:
    if not chunks:
        return "No matching knowledge was found."
    lines: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        title = chunk.title or f"Result {i}"
        source = f" ({chunk.source})" if chunk.source else ""
        lines.append(f"[{i}] {title}{source}: {chunk.content}")
    return "\n".join(lines)
