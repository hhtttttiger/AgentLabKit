from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from common.auth import CurrentUser
from common.dependencies import DbSession
from common.response import ok
from .dependencies import InvokeServiceDep
from .service import AgentNotFoundError, EmbeddingError

router = APIRouter()


class ModelTextRequest(BaseModel):
    Message: str
    SystemPrompt: str | None = None
    InvocationContext: dict | None = None


class AgentTurnHistoryItem(BaseModel):
    Role: str
    Content: str
    Name: str | None = None
    Metadata: dict[str, str] = {}


class AgentTurnRequest(BaseModel):
    Message: str
    SessionId: str | None = None
    UserId: str | None = None
    History: list[AgentTurnHistoryItem] = []


class ModelEmbeddingTestRequest(BaseModel):
    Text: str
    Dimensions: int | None = None


@router.get("/agents/options")
async def agent_options(db: DbSession, svc: InvokeServiceDep):
    return ok(await svc.list_agent_options(db))


@router.post("/agents/{agent_key}/turn")
async def agent_turn(
    agent_key: str,
    body: AgentTurnRequest,
    svc: InvokeServiceDep,
    current_user: CurrentUser,
):
    try:
        result = await svc.run_agent_turn(
            agent_key=agent_key,
            message=body.Message,
            session_id=body.SessionId,
            user_id=body.UserId or current_user["user_id"],
            history=[h.model_dump() for h in body.History],
        )
        return ok(result)
    except AgentNotFoundError:
        return JSONResponse(
            {"success": False, "msg": f"Agent '{agent_key}' not found or not published", "data": None},
            status_code=404,
        )


@router.post("/agents/{agent_key}/turn/stream")
async def agent_turn_stream(
    agent_key: str,
    body: AgentTurnRequest,
    svc: InvokeServiceDep,
    current_user: CurrentUser,
):
    try:
        generator = svc.run_agent_turn_sse_stream(
            agent_key=agent_key,
            message=body.Message,
            session_id=body.SessionId,
            user_id=body.UserId or current_user["user_id"],
            history=[h.model_dump() for h in body.History],
        )
        return StreamingResponse(generator, media_type="text/event-stream")
    except AgentNotFoundError:
        return JSONResponse(
            {"success": False, "msg": f"Agent '{agent_key}' not found or not published", "data": None},
            status_code=404,
        )


@router.post("/{model_id}/text")
async def model_text(model_id: str, body: ModelTextRequest, svc: InvokeServiceDep):
    result = await svc.generate_text(
        model_id=model_id,
        message=body.Message,
        system_prompt=body.SystemPrompt,
    )
    return ok(result)


@router.post("/{model_id}/text/stream")
async def model_text_stream(model_id: str, body: ModelTextRequest, svc: InvokeServiceDep):
    generator = svc.generate_text_sse_stream(
        model_id=model_id,
        message=body.Message,
        system_prompt=body.SystemPrompt,
    )
    return StreamingResponse(generator, media_type="text/event-stream")


@router.post("/{model_id}/text/test-stream")
async def model_text_test_stream(model_id: str, body: ModelTextRequest, svc: InvokeServiceDep):
    generator = svc.generate_text_test_sse_stream(
        model_id=model_id,
        message=body.Message,
        system_prompt=body.SystemPrompt,
    )
    return StreamingResponse(generator, media_type="text/event-stream")


@router.post("/{model_id}/embedding/test")
async def model_embedding_test(
    model_id: str,
    body: ModelEmbeddingTestRequest,
    svc: InvokeServiceDep,
):
    try:
        result = await svc.generate_embedding_test(
            model_id=model_id,
            text=body.Text,
            dimensions=body.Dimensions,
        )
        return ok(result)
    except EmbeddingError as e:
        return JSONResponse(
            {
                "success": False,
                "error": {"message": e.message, "code": e.code},
                "latencyMs": e.latency_ms,
            },
            status_code=500,
        )
