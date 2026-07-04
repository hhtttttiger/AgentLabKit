"""Keyword-based output guard for basic harmful-content blocking."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import ClassVar, Literal

from ..contracts import GuardContext, GuardResult, GuardVerdict


@dataclass(slots=True)
class ContentSafetyGuard:
    """Block high-risk content categories via lightweight pattern matching.

    ``block_categories`` must be a subset of :attr:`_CATEGORY_PATTERNS` keys.
    Passing an unknown category raises :class:`ValueError` at construction time
    so misconfiguration is caught early rather than silently ignored at runtime.
    """

    name: ClassVar[str] = "content_safety"
    phase: ClassVar[Literal["output"]] = "output"

    _CATEGORY_PATTERNS: ClassVar[dict[str, tuple[re.Pattern[str], ...]]] = {
        "violence": (
            re.compile(r"\bhow\s+to\s+(kill|murder|stab|shoot|poison)\b", re.IGNORECASE),
            re.compile(r"\b(build|make)\s+(a\s+)?bomb\b", re.IGNORECASE),
            re.compile(r"\bviolent\s+attack\b", re.IGNORECASE),
        ),
        "self_harm": (
            re.compile(r"\bhow\s+to\s+(kill|harm)\s+myself\b", re.IGNORECASE),
            re.compile(r"\bsuicide\s+method\b", re.IGNORECASE),
            re.compile(r"\bself[-\s]?harm\b", re.IGNORECASE),
        ),
        "hate_speech": (
            re.compile(r"\bexterminate\s+(all\s+)?\w+\s+people\b", re.IGNORECASE),
            re.compile(r"\bcleanse\s+\w+\s+from\s+society\b", re.IGNORECASE),
        ),
    }

    block_categories: frozenset[str] = field(
        default_factory=lambda: frozenset({"violence", "self_harm"})
    )

    def __post_init__(self) -> None:
        unknown = self.block_categories - frozenset(self._CATEGORY_PATTERNS)
        if unknown:
            raise ValueError(
                f"Unknown content safety categories: {sorted(unknown)!r}. "
                f"Known categories: {sorted(self._CATEGORY_PATTERNS)!r}"
            )

    async def evaluate(self, context: GuardContext) -> GuardResult:
        text = context.message or ""
        for category in sorted(self.block_categories):
            for pattern in self._CATEGORY_PATTERNS.get(category, ()):
                if pattern.search(text):
                    return GuardResult(
                        verdict=GuardVerdict.BLOCK,
                        guard_name=self.name,
                        reason=f"content_safety:{category}",
                        details={"category": category, "pattern": pattern.pattern},
                    )

        return GuardResult(
            verdict=GuardVerdict.PASS,
            guard_name=self.name,
        )
