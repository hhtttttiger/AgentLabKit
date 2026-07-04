"""Prompt-injection detection guard (rule + heuristic, zero external calls)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar, Literal

from ..contracts import GuardContext, GuardResult, GuardVerdict

# Each tuple: (compiled_regex, weight).
# Weights reflect severity: higher = stronger injection signal.
_PATTERN_DEFS: list[tuple[str, float]] = [
    # ── Instruction override ──────────────────────────────
    (r"ignore\s+(all\s+)?(previous|above|prior|earlier|preceding)\s+(instructions|rules|prompts|directives|guidelines)", 0.9),
    (r"disregard\s+(all\s+)?(previous|above|prior|your)\s+(instructions|rules|prompts)", 0.9),
    (r"forget\s+(everything|all|your)\s+(instructions|rules|training|context|guidelines)", 0.85),
    (r"do\s+not\s+follow\s+(any|your|the)\s+(previous|prior|above|original)\s+(instructions|rules)", 0.85),
    (r"override\s+(your|all|the)\s+(instructions|rules|guidelines|safety|restrictions)", 0.85),

    # ── Role-play / persona hijack ────────────────────────
    (r"you\s+are\s+now\s+", 0.7),
    (r"pretend\s+(you\s+are|to\s+be)\s+", 0.7),
    (r"act\s+as\s+(if\s+)?(you\s+)?(are|were)\s+", 0.6),
    (r"from\s+now\s+on[\s,]+you\s+(are|will|must|should)", 0.7),
    (r"i\s+want\s+you\s+to\s+(act|behave|pretend|roleplay)\s+as\s+", 0.65),
    (r"switch\s+to\s+.{0,30}mode", 0.6),

    # ── System prompt extraction ──────────────────────────
    (r"reveal\s+(your|the|all)\s+(secret|system|hidden|internal|original)\s*(prompt|instructions|rules)?", 0.85),
    (r"output\s+(your|the)\s+(system\s+)?prompt", 0.85),
    (r"(show|display|print|repeat|echo)\s+(me\s+)?(your|the)\s+(system\s+)?(prompt|instructions)", 0.8),
    (r"what\s+(are|is|were)\s+your\s+(system\s+)?(instructions|prompt|rules|guidelines)", 0.5),

    # ── Special-token injection ───────────────────────────
    (r"<\|?(system|im_start|im_end|endoftext|startoftext)\|?>", 0.95),
    (r"\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>", 0.95),
    (r"###\s*(system|instruction|human|assistant)\s*:", 0.8),

    # ── Encoding / obfuscation attempts ───────────────────
    (r"base64[\s:]+[A-Za-z0-9+/=]{20,}", 0.6),
    (r"(rot13|hex|decode|encode)\s+(this|the|my|following)", 0.5),

    # ── Constraint removal ────────────────────────────────
    (r"(remove|disable|turn\s+off|bypass|skip)\s+(all\s+)?(safety|content|ethical|security)\s*(filters?|restrictions?|guidelines?|checks?|policies)?", 0.85),
    (r"(there\s+are\s+)?no\s+(rules|restrictions|limits|boundaries|guidelines)\s+(anymore|now|here|apply)", 0.75),
    (r"jailbreak", 0.9),
    (r"DAN\s+mode|do\s+anything\s+now", 0.9),
]

_COMPILED_PATTERNS: list[tuple[re.Pattern[str], float]] = [
    (re.compile(pattern, re.IGNORECASE), weight)
    for pattern, weight in _PATTERN_DEFS
]


@dataclass(slots=True)
class PromptInjectionGuard:
    """Rule-based prompt-injection detector.

    Scans the input against a curated set of weighted regex patterns.
    The cumulative score (capped at 1.0) is compared to ``block_threshold``.

    Designed for near-zero latency; no external API calls.
    """

    name: ClassVar[str] = "prompt_injection"
    phase: ClassVar[Literal["input"]] = "input"

    block_threshold: float = 0.7

    async def evaluate(self, context: GuardContext) -> GuardResult:
        score, matched = self._score(context.message or "")
        if score >= self.block_threshold:
            return GuardResult(
                verdict=GuardVerdict.BLOCK,
                guard_name=self.name,
                reason="prompt_injection_detected",
                confidence=min(score, 1.0),
                details={"matched_patterns": matched},
            )
        return GuardResult(
            verdict=GuardVerdict.PASS,
            guard_name=self.name,
            confidence=min(score, 1.0),
        )

    @staticmethod
    def _score(text: str) -> tuple[float, list[str]]:
        """Return (cumulative_score, list_of_matched_pattern_strings)."""
        total = 0.0
        matched: list[str] = []
        for pattern, weight in _COMPILED_PATTERNS:
            if pattern.search(text):
                total += weight
                matched.append(pattern.pattern)
        return total, matched
