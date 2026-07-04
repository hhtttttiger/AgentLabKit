from __future__ import annotations

from dataclasses import dataclass

from ..contracts.models import AgentMessage, AgentRole
from .message_priority import (
    MEMORY_KIND_METADATA_KEY,
    MEMORY_KIND_SUMMARY,
    MessagePriority,
    is_summary_message,
    resolve_message_priority,
)
from .summarizer import Summarizer
from .token_counter import TokenCounter


@dataclass(slots=True)
class ContextWindowConfig:
    max_total_tokens: int = 8000
    reserve_for_response: int = 1500
    reserve_for_system: int = 1500
    summarize_threshold_ratio: float = 0.8
    min_recent_messages: int = 4
    enable_summarization: bool = True


@dataclass(slots=True)
class ContextWindow:
    summary: AgentMessage | None
    pinned: list[AgentMessage]
    recent: list[AgentMessage]
    total_tokens: int
    budget_tokens: int
    dropped_count: int
    summarized_count: int

    def to_messages(self) -> list[AgentMessage]:
        messages: list[AgentMessage] = []
        if self.summary is not None:
            messages.append(self.summary)
        messages.extend(self.pinned)
        messages.extend(self.recent)
        return messages


class ContextManager:
    def __init__(
        self,
        config: ContextWindowConfig,
        token_counter: TokenCounter,
        summarizer: Summarizer | None = None,
    ) -> None:
        self.config = config
        self.token_counter = token_counter
        self.summarizer = summarizer

    async def prepare_context(
        self,
        *,
        system_prompt: str,
        history: list[AgentMessage],
        user_message: str,
    ) -> ContextWindow:
        budget_tokens = self._compute_budget_tokens(
            system_prompt=system_prompt,
            user_message=user_message,
        )
        existing_summary = self._extract_summary(history)
        pinned, candidates, recent = self._partition_messages(history)

        selected_candidates = self._select_candidates(
            candidates=candidates,
            pinned=pinned,
            recent=recent,
            summary=existing_summary,
            budget_tokens=budget_tokens,
        )
        omitted_candidates = [
            message for message in candidates if message not in selected_candidates
        ]

        summary = existing_summary
        summarized_count = 0
        dropped_count = len(omitted_candidates)

        if self._should_summarize(history=history, omitted_candidates=omitted_candidates, budget_tokens=budget_tokens):
            source_messages: list[AgentMessage] = []
            if existing_summary is not None:
                source_messages.append(existing_summary)
            source_messages.extend(omitted_candidates)
            generated_summary = await self._summarize_messages(source_messages)
            if generated_summary is not None:
                summary = generated_summary
                summarized_count = len(omitted_candidates)
                dropped_count = 0

        summary, selected_candidates = self._fit_summary_with_budget(
            summary=summary,
            selected_candidates=selected_candidates,
            pinned=pinned,
            recent=recent,
            budget_tokens=budget_tokens,
        )
        recent_bucket = [*selected_candidates, *recent]
        total_tokens = self.token_counter.count_messages(
            ([summary] if summary is not None else []) + pinned + recent_bucket
        )
        return ContextWindow(
            summary=summary,
            pinned=pinned,
            recent=recent_bucket,
            total_tokens=total_tokens,
            budget_tokens=budget_tokens,
            dropped_count=dropped_count,
            summarized_count=summarized_count,
        )

    def _partition_messages(
        self,
        history: list[AgentMessage],
    ) -> tuple[list[AgentMessage], list[AgentMessage], list[AgentMessage]]:
        materialized = [message for message in history if not is_summary_message(message)]
        if not materialized:
            return [], [], []

        recent_cutoff = max(0, len(materialized) - self.config.min_recent_messages)
        pinned: list[AgentMessage] = []
        candidates: list[AgentMessage] = []
        recent: list[AgentMessage] = []

        for index, message in enumerate(materialized):
            priority = resolve_message_priority(message)
            if priority is MessagePriority.PINNED:
                pinned.append(message)
                continue
            if index >= recent_cutoff:
                recent.append(message)
            else:
                candidates.append(message)
        return pinned, candidates, recent

    def _compute_budget_tokens(
        self,
        *,
        system_prompt: str,
        user_message: str,
    ) -> int:
        reserved = (
            self.config.reserve_for_response
            + self.config.reserve_for_system
            + self.token_counter.count(system_prompt)
            + self.token_counter.count(user_message)
        )
        return max(self.config.max_total_tokens - reserved, 0)

    def _select_candidates(
        self,
        *,
        candidates: list[AgentMessage],
        pinned: list[AgentMessage],
        recent: list[AgentMessage],
        summary: AgentMessage | None,
        budget_tokens: int,
    ) -> list[AgentMessage]:
        selected_indices: set[int] = set()
        base_tokens = self.token_counter.count_messages(
            ([summary] if summary is not None else []) + pinned + recent
        )
        remaining_budget = budget_tokens - base_tokens
        if remaining_budget <= 0:
            return []

        indexed = list(enumerate(candidates))
        for priority in (MessagePriority.NORMAL, MessagePriority.LOW):
            for idx, message in reversed(indexed):
                if idx in selected_indices:
                    continue
                if resolve_message_priority(message) is not priority:
                    continue
                message_tokens = self.token_counter.count_messages([message])
                if message_tokens > remaining_budget:
                    continue
                selected_indices.add(idx)
                remaining_budget -= message_tokens

        return [msg for idx, msg in enumerate(candidates) if idx in selected_indices]

    def _should_summarize(
        self,
        *,
        history: list[AgentMessage],
        omitted_candidates: list[AgentMessage],
        budget_tokens: int,
    ) -> bool:
        if (
            not omitted_candidates
            or not self.config.enable_summarization
            or self.summarizer is None
        ):
            return False
        effective_history = [
            message for message in history if not is_summary_message(message)
        ]
        history_tokens = self.token_counter.count_messages(effective_history)
        threshold = int(budget_tokens * self.config.summarize_threshold_ratio)
        return history_tokens >= threshold

    async def _summarize_messages(
        self,
        messages: list[AgentMessage],
    ) -> AgentMessage | None:
        if not messages or self.summarizer is None:
            return None
        try:
            summary_text = (await self.summarizer.summarize(messages)).strip()
        except Exception:
            return None
        if not summary_text:
            return None
        return AgentMessage(
            role=AgentRole.SYSTEM,
            content=summary_text,
            metadata={MEMORY_KIND_METADATA_KEY: MEMORY_KIND_SUMMARY},
        )

    def _fit_summary_with_budget(
        self,
        *,
        summary: AgentMessage | None,
        selected_candidates: list[AgentMessage],
        pinned: list[AgentMessage],
        recent: list[AgentMessage],
        budget_tokens: int,
    ) -> tuple[AgentMessage | None, list[AgentMessage]]:
        kept_candidates = list(selected_candidates)
        if summary is None:
            return None, kept_candidates

        while kept_candidates:
            total = self.token_counter.count_messages(
                [summary, *pinned, *kept_candidates, *recent]
            )
            if total <= budget_tokens:
                return summary, kept_candidates
            kept_candidates.pop(0)

        total = self.token_counter.count_messages([summary, *pinned, *recent])
        if total <= budget_tokens:
            return summary, kept_candidates
        return None, kept_candidates

    @staticmethod
    def _extract_summary(history: list[AgentMessage]) -> AgentMessage | None:
        for message in history:
            if is_summary_message(message):
                return message
        return None
