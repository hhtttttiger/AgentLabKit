"""ObservabilityModule — 遵循项目统一的 Module 模式。"""

from __future__ import annotations

from dataclasses import dataclass

from .config import ObservabilitySettings
from .trace_store import TraceStore, PostgresTraceStore


@dataclass(slots=True)
class ObservabilityModule:
    settings: ObservabilitySettings
    trace_store: TraceStore


def create_observability_module(
    *,
    session_factory,
    settings: ObservabilitySettings | None = None,
) -> ObservabilityModule:
    settings = settings or ObservabilitySettings()
    trace_store = PostgresTraceStore(session_factory)
    return ObservabilityModule(
        settings=settings,
        trace_store=trace_store,
    )
