from __future__ import annotations

from math import ceil
from typing import Protocol

from ..contracts.models import AgentMessage


class TokenCounter(Protocol):
    def count(self, text: str) -> int:
        ...

    def count_messages(self, messages: list[AgentMessage]) -> int:
        ...


class ApproximateTokenCounter:
    """Fallback counter used when tiktoken is unavailable."""

    def __init__(self, chars_per_token: float = 4.0) -> None:
        self._chars_per_token = chars_per_token

    def count(self, text: str) -> int:
        if not text:
            return 0
        return max(1, ceil(len(text) / self._chars_per_token))

    def count_messages(self, messages: list[AgentMessage]) -> int:
        total = 0
        for message in messages:
            total += 4
            total += self.count(message.content)
            if message.name:
                total += self.count(message.name)
        return total


class TiktokenCounter:
    """tiktoken-backed counter for OpenAI-compatible budgeting."""

    def __init__(self, model: str = "gpt-5.4-mini") -> None:
        try:
            import tiktoken
        except ImportError as exc:
            raise RuntimeError(
                "tiktoken is required for TiktokenCounter. Install the 'memory' extra."
            ) from exc

        try:
            self._encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            self._encoding = tiktoken.get_encoding("cl100k_base")

    def count(self, text: str) -> int:
        if not text:
            return 0
        return len(self._encoding.encode(text))

    def count_messages(self, messages: list[AgentMessage]) -> int:
        total = 0
        for message in messages:
            total += 4
            total += self.count(message.content)
            if message.name:
                total += self.count(message.name)
        return total


def create_default_token_counter(model: str = "gpt-5.4-mini") -> TokenCounter:
    try:
        return TiktokenCounter(model=model)
    except Exception:
        return ApproximateTokenCounter()
