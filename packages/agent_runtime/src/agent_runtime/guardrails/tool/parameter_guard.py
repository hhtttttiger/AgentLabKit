"""Tool-parameter guard for basic length and injection checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar, Literal

from ..contracts import GuardContext, GuardResult, GuardVerdict


@dataclass(slots=True)
class ParameterGuard:
    """Validate tool-call arguments before execution."""

    name: ClassVar[str] = "parameter_validation"
    phase: ClassVar[Literal["tool"]] = "tool"

    _SUSPICIOUS_PATTERNS: ClassVar[tuple[re.Pattern[str], ...]] = (
        re.compile(
            r"\b(select|union|insert|update|delete|drop|truncate)\b.{0,40}(--|/\*|;)",
            re.IGNORECASE,
        ),
        re.compile(r"\b(or|and)\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+['\"]?", re.IGNORECASE),
        re.compile(r"<script\b|javascript:", re.IGNORECASE),
        re.compile(r"\b(rm\s+-rf|curl\s+https?://|wget\s+https?://|powershell\s+-enc)\b", re.IGNORECASE),
        re.compile(r"(\$\(|`.+`|\|\||&&|;\s*\w+)", re.IGNORECASE),
    )

    max_string_length: int = 2000

    async def evaluate(self, context: GuardContext) -> GuardResult:
        for path, value in self._walk(context.tool_arguments or {}, path="arguments"):
            if isinstance(value, str):
                if len(value) > self.max_string_length:
                    return GuardResult(
                        verdict=GuardVerdict.BLOCK,
                        guard_name=self.name,
                        reason=f"parameter_too_long:{path}",
                        details={
                            "path": path,
                            "length": len(value),
                            "max_string_length": self.max_string_length,
                        },
                    )
                if self._contains_injection(value):
                    return GuardResult(
                        verdict=GuardVerdict.BLOCK,
                        guard_name=self.name,
                        reason=f"parameter_injection:{path}",
                        details={"path": path},
                    )

        return GuardResult(
            verdict=GuardVerdict.PASS,
            guard_name=self.name,
        )

    @classmethod
    def _contains_injection(cls, value: str) -> bool:
        return any(pattern.search(value) for pattern in cls._SUSPICIOUS_PATTERNS)

    @classmethod
    def _walk(cls, value: Any, *, path: str) -> list[tuple[str, Any]]:
        items: list[tuple[str, Any]] = []
        if isinstance(value, dict):
            for key, nested in value.items():
                items.extend(cls._walk(nested, path=f"{path}.{key}"))
            return items
        if isinstance(value, list):
            for index, nested in enumerate(value):
                items.extend(cls._walk(nested, path=f"{path}[{index}]"))
            return items
        items.append((path, value))
        return items
