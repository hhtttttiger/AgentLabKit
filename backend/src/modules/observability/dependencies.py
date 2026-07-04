"""可观测性依赖注入。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from observability import ObservabilityModule
from observability.trace_store import TraceStore


def get_observability_module(request: Request) -> ObservabilityModule:
    mod: ObservabilityModule | None = getattr(request.app.state, "observability_module", None)
    if mod is None:
        raise RuntimeError("ObservabilityModule not initialized — check lifespan wiring")
    return mod


def get_trace_store(mod: ObservabilityModule = Depends(get_observability_module)) -> TraceStore:
    return mod.trace_store


TraceStoreDep = Annotated[TraceStore, Depends(get_trace_store)]
