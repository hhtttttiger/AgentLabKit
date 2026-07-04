"""Message building utilities — conversation history, tool schemas, raw message normalization.

Extracted from ``engine.py`` to isolate message construction logic.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from ..contracts.models import AgentMessage, AgentRole, AgentTurnRequest

if TYPE_CHECKING:
    from ..config import AgentSettings
    from ..tools import ToolBinding, ToolRegistry


class MessageBuilder:
    """Stateless helper for building messages — methods extracted from ``AgentRuntime``."""

    @staticmethod
    def normalize_raw_messages(messages: list[Any]) -> list[AgentMessage]:
        """Convert internal message objects to ``AgentMessage`` list.

        This handles both the old pydantic-ai ``ModelMessage`` format and
        the new plain ``AgentMessage`` format.
        """
        normalized: list[AgentMessage] = []
        for message in messages:
            # Already an AgentMessage
            if isinstance(message, AgentMessage):
                normalized.append(message)
                continue

            # pydantic-ai ModelMessage (legacy — still supported during migration)
            message_type = type(message).__name__
            if message_type == "ModelRequest":
                for part in getattr(message, "parts", []):
                    part_type = type(part).__name__
                    if part_type == "UserPromptPart":
                        normalized.append(
                            AgentMessage(
                                role=AgentRole.USER,
                                content=MessageBuilder._stringify(part.content),
                            )
                        )
                    elif part_type == "SystemPromptPart":
                        normalized.append(
                            AgentMessage(role=AgentRole.SYSTEM, content=part.content)
                        )
                    elif part_type == "ToolReturnPart":
                        normalized.append(
                            AgentMessage(
                                role=AgentRole.TOOL,
                                name=part.tool_name,
                                content=MessageBuilder._stringify(part.content),
                            )
                        )
            elif message_type == "ModelResponse":
                for part in getattr(message, "parts", []):
                    part_type = type(part).__name__
                    if part_type == "TextPart":
                        normalized.append(
                            AgentMessage(role=AgentRole.ASSISTANT, content=part.content)
                        )
                    elif part_type == "ToolCallPart" and part.tool_name != "final_result":
                        normalized.append(
                            AgentMessage(
                                role=AgentRole.ASSISTANT,
                                name=part.tool_name,
                                content=MessageBuilder._stringify(part.args),
                            )
                        )
        return normalized

    @staticmethod
    def _stringify(value: Any) -> str:
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, ensure_ascii=True)
        except TypeError:
            return str(value)

    @staticmethod
    def replace_terminal_assistant_message(
        raw_messages: list[AgentMessage],
        reply_text: str,
    ) -> list[AgentMessage]:
        """Replace the last assistant message's content with *reply_text*."""
        normalized = [message.model_copy(deep=True) for message in raw_messages]
        for index in range(len(normalized) - 1, -1, -1):
            if normalized[index].role is AgentRole.ASSISTANT:
                normalized[index] = normalized[index].model_copy(
                    update={"content": reply_text}
                )
                return normalized
        normalized.append(AgentMessage(role=AgentRole.ASSISTANT, content=reply_text))
        return normalized

    @staticmethod
    def annotate_terminal_assistant_message(
        raw_messages: list[AgentMessage],
        *,
        reply_text: str,
        metadata: dict[str, str],
    ) -> list[AgentMessage]:
        """Annotate the last assistant message with metadata."""
        normalized = [message.model_copy(deep=True) for message in raw_messages]
        for index in range(len(normalized) - 1, -1, -1):
            if normalized[index].role is AgentRole.ASSISTANT:
                combined_meta = {**normalized[index].metadata, **metadata}
                normalized[index] = normalized[index].model_copy(
                    update={"content": reply_text, "metadata": combined_meta}
                )
                return normalized
        normalized.append(
            AgentMessage(role=AgentRole.ASSISTANT, content=reply_text, metadata=metadata)
        )
        return normalized

    @staticmethod
    def build_tool_schemas(
        tool_registry: ToolRegistry,
        settings: AgentSettings,
        allowed_tool_names: frozenset[str] | None = None,
        tool_bindings: list[ToolBinding] | None = None,
    ) -> list[dict[str, Any]]:
        """Build tool definition dicts for LLM prompt injection.

        Returns a list of dicts with ``name``, ``description``, ``parameters`` keys.
        """
        return tool_registry.tool_definitions(
            settings,
            allowed_tool_names=allowed_tool_names,
            tool_bindings=tool_bindings,
        )


__all__ = ["MessageBuilder"]
