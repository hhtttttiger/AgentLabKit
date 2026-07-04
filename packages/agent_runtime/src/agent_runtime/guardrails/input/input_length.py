"""Input-length guard — blocks excessively long messages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Literal

from ..contracts import GuardContext, GuardResult, GuardVerdict


@dataclass(slots=True)
class InputLengthGuard:
    """Reject inputs that exceed a character-count ceiling.

    Token-based limit is intentionally omitted in the MVP to avoid
    a dependency on ``tiktoken`` at the guardrails layer; the memory
    module's ``ContextManager`` already handles token budgeting.
    """

    name: ClassVar[str] = "input_length"
    phase: ClassVar[Literal["input"]] = "input"

    max_chars: int = 10_000

    async def evaluate(self, context: GuardContext) -> GuardResult:
        length = len(context.message or "")
        if length > self.max_chars:
            return GuardResult(
                verdict=GuardVerdict.BLOCK,
                guard_name=self.name,
                reason="input_too_long",
                details={"length": length, "max_chars": self.max_chars},
            )
        return GuardResult(
            verdict=GuardVerdict.PASS,
            guard_name=self.name,
            details={"length": length},
        )
