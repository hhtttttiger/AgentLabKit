"""Repository abstraction for loading the active global guardrails snapshot."""

from __future__ import annotations

from typing import Protocol

from .global_snapshot import (
    GlobalGuardrailsSnapshot,
    clone_global_guardrails_snapshot,
)


class GlobalGuardrailsRepository(Protocol):
    async def get_active_snapshot(self) -> GlobalGuardrailsSnapshot | None:
        """Return the current active global snapshot, if one exists."""
        ...


class StaticGlobalGuardrailsRepository:
    """Simple in-memory repository used by tests."""

    def __init__(self, snapshot: GlobalGuardrailsSnapshot | None) -> None:
        self._snapshot = clone_global_guardrails_snapshot(snapshot)

    async def get_active_snapshot(self) -> GlobalGuardrailsSnapshot | None:
        return clone_global_guardrails_snapshot(self._snapshot)
