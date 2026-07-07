"""Provider adapter implementations."""

from .anthropic import AnthropicTextAdapter
from .openai import (
    CompositeSpeechBatchAdapter,
    CompositeSpeechStreamAdapter,
    OpenAIChatSpeechBatchAdapter,
    OpenAIChatSpeechStreamAdapter,
    OpenAIImageAdapter,
    OpenAIRealtimeAdapter,
    OpenAISpeechBatchAdapter,
    OpenAISpeechStreamAdapter,
    OpenAITextAdapter,
    OpenAITranscriptionStreamAdapter,
)

__all__ = [
    "AnthropicTextAdapter",
    "CompositeSpeechBatchAdapter",
    "CompositeSpeechStreamAdapter",
    "OpenAIChatSpeechBatchAdapter",
    "OpenAIChatSpeechStreamAdapter",
    "OpenAIImageAdapter",
    "OpenAIRealtimeAdapter",
    "OpenAISpeechBatchAdapter",
    "OpenAISpeechStreamAdapter",
    "OpenAITextAdapter",
    "OpenAITranscriptionStreamAdapter",
]
