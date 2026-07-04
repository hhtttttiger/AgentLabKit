"""Regex-based output guard that masks common PII patterns."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import ClassVar, Literal

from ..contracts import GuardContext, GuardResult, GuardVerdict


@dataclass(slots=True)
class PiiMaskingGuard:
    """Mask common PII categories in model output text."""

    name: ClassVar[str] = "pii_masking"
    phase: ClassVar[Literal["output"]] = "output"

    _PATTERNS: ClassVar[dict[str, re.Pattern[str]]] = {
        "email": re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
            re.IGNORECASE,
        ),
        "phone_cn": re.compile(r"(?<!\d)(?:\+?86[-.\s]?)?1[3-9]\d{9}(?!\d)"),
        "id_card_cn": re.compile(r"\b\d{17}[\dXx]\b"),
        "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
        "ssn_us": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    }
    _REPLACEMENTS: ClassVar[dict[str, str]] = {
        "email": "[REDACTED:EMAIL]",
        "phone_cn": "[REDACTED:PHONE]",
        "id_card_cn": "[REDACTED:CN_ID]",
        "credit_card": "[REDACTED:CARD]",
        "ssn_us": "[REDACTED:SSN]",
    }

    categories: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {"email", "phone_cn", "id_card_cn", "credit_card"}
        )
    )

    async def evaluate(self, context: GuardContext) -> GuardResult:
        masked_text = context.message or ""
        found_types: list[str] = []
        match_count = 0

        for category in self.categories:
            pattern = self._PATTERNS.get(category)
            if pattern is None:
                continue

            masked_text, replacements = pattern.subn(
                self._REPLACEMENTS.get(category, "[REDACTED]"),
                masked_text,
            )
            if replacements > 0:
                found_types.append(category)
                match_count += replacements

        if not found_types:
            return GuardResult(
                verdict=GuardVerdict.PASS,
                guard_name=self.name,
            )

        return GuardResult(
            verdict=GuardVerdict.MODIFY,
            guard_name=self.name,
            reason="pii_masked",
            modified_text=masked_text,
            details={
                "types": sorted(found_types),
                "match_count": match_count,
            },
        )
