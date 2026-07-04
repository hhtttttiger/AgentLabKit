from __future__ import annotations

from textwrap import dedent
from typing import Protocol

from llm_gateway import GatewayService, TextGenerateRequest

from ..contracts.models import AgentMessage


class Summarizer(Protocol):
    async def summarize(
        self,
        messages: list[AgentMessage],
        context_hint: str | None = None,
    ) -> str:
        ...


class GatewaySummarizer:
    SUMMARIZE_PROMPT = dedent(
        """\
        Summarize the following conversation into a concise paragraph.
        Preserve: key facts, decisions, action items, names, numbers, and dates.
        Discard: greetings, filler, and repeated confirmations.
        Output only the summary text.

        {context_hint}
        Conversation:
        {conversation}
        """
    ).strip()

    _DEFAULT_MAX_SUMMARY_TOKENS = 512

    def __init__(
        self,
        gateway: GatewayService,
        *,
        model: str | None = None,
        max_output_tokens: int | None = None,
    ) -> None:
        self.gateway = gateway
        self.model = model
        self.max_output_tokens = max_output_tokens or self._DEFAULT_MAX_SUMMARY_TOKENS

    async def summarize(
        self,
        messages: list[AgentMessage],
        context_hint: str | None = None,
    ) -> str:
        if not messages:
            return ""

        prompt = self.SUMMARIZE_PROMPT.format(
            context_hint=(f"Context hint: {context_hint}\n" if context_hint else ""),
            conversation=self._render_messages(messages),
        )
        response = await self.gateway.generate_text(
            TextGenerateRequest(
                model=self.model,
                prompt=prompt,
                structured=False,
                max_output_tokens=self.max_output_tokens,
            )
        )
        return response.text.strip()

    @staticmethod
    def _render_messages(messages: list[AgentMessage]) -> str:
        return "\n".join(
            f"[{message.role.value}] {message.content}"
            if not message.name
            else f"[{message.role.value}:{message.name}] {message.content}"
            for message in messages
        )
