"""DI wiring for ai_invoke module."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from alkit_db.engine import get_session_factory
from .service import InvokeService


def get_invoke_service(request: Request) -> InvokeService:
    gateway = getattr(request.app.state, "gateway_service", None)
    if gateway is None:
        raise RuntimeError(
            "GatewayService not initialized. Check gateway_catalog_database_url config."
        )

    runtime = getattr(request.app.state, "agent_runtime", None)
    if runtime is None:
        raise RuntimeError(
            "AgentRuntime not initialized. Check lifespan agent_runtime setup."
        )

    loader = getattr(request.app.state, "agent_definition_loader", None)

    return InvokeService(
        gateway_service=gateway,
        agent_runtime=runtime,
        agent_definition_loader=loader,
        session_factory=get_session_factory(),
    )


InvokeServiceDep = Annotated[InvokeService, Depends(get_invoke_service)]
