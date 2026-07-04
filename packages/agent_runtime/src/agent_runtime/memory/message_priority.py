from __future__ import annotations

from enum import Enum

from ..contracts.models import AgentMessage

PRIORITY_METADATA_KEY = "_priority"
MEMORY_KIND_METADATA_KEY = "_memory_kind"
MEMORY_KIND_SUMMARY = "summary"


class MessagePriority(str, Enum):
    PINNED = "pinned"
    NORMAL = "normal"
    LOW = "low"


def resolve_message_priority(message: AgentMessage) -> MessagePriority:
    raw_value = (message.metadata.get(PRIORITY_METADATA_KEY) or "").strip().lower()
    try:
        return MessagePriority(raw_value)
    except ValueError:
        return MessagePriority.NORMAL


def mark_message_priority(
    message: AgentMessage,
    priority: MessagePriority,
) -> AgentMessage:
    metadata = dict(message.metadata)
    metadata[PRIORITY_METADATA_KEY] = priority.value
    return message.model_copy(update={"metadata": metadata})


def is_pinned_message(message: AgentMessage) -> bool:
    return resolve_message_priority(message) is MessagePriority.PINNED


def is_summary_message(message: AgentMessage) -> bool:
    return (
        (message.metadata.get(MEMORY_KIND_METADATA_KEY) or "").strip().lower()
        == MEMORY_KIND_SUMMARY
    )
