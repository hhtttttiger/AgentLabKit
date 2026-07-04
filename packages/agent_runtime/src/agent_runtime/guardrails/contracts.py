"""Guard protocol, result types, and shared contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, Protocol, runtime_checkable


class GuardVerdict(str, Enum):
    """Three-level guard decision."""

    PASS = "pass"
    MODIFY = "modify"
    BLOCK = "block"


@dataclass(slots=True)
class GuardContext:
    """Immutable context passed to each guard's ``evaluate`` call.

    ``message`` carries the text being inspected for *input* and *output*
    phases.  It is ``None`` for *tool* phase — tool guards use
    ``tool_arguments`` instead.
    """

    phase: Literal["input", "output", "tool"]
    message: str | None = None
    session_id: str = ""
    trace_id: str = ""
    tool_name: str | None = None
    tool_arguments: dict[str, Any] | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class GuardResult:
    """Outcome produced by a single guard."""

    verdict: GuardVerdict
    guard_name: str
    reason: str | None = None
    modified_text: str | None = None
    confidence: float = 1.0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GuardPipelineResult:
    """Aggregated outcome of running all guards in a phase."""

    final_verdict: GuardVerdict
    results: list[GuardResult] = field(default_factory=list)
    modified_text: str | None = None
    blocked_by: str | None = None
    block_reason: str | None = None


@runtime_checkable
class Guard(Protocol):
    """Protocol every guard must satisfy."""

    @property
    def name(self) -> str: ...

    @property
    def phase(self) -> Literal["input", "output", "tool"]: ...

    async def evaluate(self, context: GuardContext) -> GuardResult: ...


class GuardAuditCallback(Protocol):
    """Optional callback invoked after each guard evaluation for audit logging."""

    async def on_guard_result(
        self,
        phase: str,
        result: GuardResult,
        context: GuardContext,
    ) -> None: ...
