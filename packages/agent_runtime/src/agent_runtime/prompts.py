from __future__ import annotations

from .config import AgentSettings
from .contracts.models import AgentTurnRequest, KnowledgeChunk


def build_system_prompt(settings: AgentSettings, request: AgentTurnRequest) -> str:
    context_lines = [
        settings.default_system_prompt,
        "Answer with the least complicated correct explanation.",
        "Use tools only when they materially improve accuracy.",
        "Prefer solving the issue directly before suggesting handoff.",
        "Only suggest handoff when the request cannot be completed with the available information and tools.",
    ]

    if request.locale:
        context_lines.append(f"Preferred locale: {request.locale}.")
    if request.channel:
        context_lines.append(f"Conversation channel: {request.channel}.")
    if request.customer_id:
        context_lines.append(f"Customer id: {request.customer_id}.")

    if request.knowledge_chunks:
        context_lines.extend(
            [
                "Retrieved knowledge below comes from the current knowledge base.",
                "When the retrieved knowledge answers the user directly, prefer it over general model knowledge.",
                "If the answer depends on an exact value present in the retrieved knowledge, preserve that value exactly.",
                _render_knowledge_chunks(request.knowledge_chunks),
            ]
        )
    elif request.knowledge_lookup_status == "miss":
        context_lines.append(
            "A knowledge lookup was attempted for this turn but no matching knowledge was found. For document-specific requests, say that no matching knowledge was found instead of inventing details."
        )

    return "\n".join(context_lines)


def _render_knowledge_chunks(chunks: list[KnowledgeChunk]) -> str:
    lines = ["Retrieved knowledge:"]
    for index, chunk in enumerate(chunks, start=1):
        source = chunk.source or chunk.title or f"knowledge-{index}"
        lines.append(f"[{index}] source={source}")
        lines.append(chunk.content)
    return "\n".join(lines)
