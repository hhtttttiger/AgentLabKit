from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from agent_runtime import AgentMessage, AgentRole
from common.auth import CurrentUser
from common.dependencies import DbSession
from alkit_db.engine import get_session_factory
from common.response import ok
from application import ExecuteAgent, ExecuteAgentCommand
from .agent_turn import run_execute_agent_stream
from .dependencies import ExecuteAgentDep, InvokeServiceDep
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
    execute_agent: ExecuteAgentDep,
    current_user: CurrentUser,
):
    try:
        command = ExecuteAgentCommand(
            agent_key=agent_key,
            input=body.Message,
            session_id=body.SessionId,
            user_id=body.UserId or current_user["user_id"],
            history=tuple(
                AgentMessage(
                    role=AgentRole(item.Role.lower()), content=item.Content,
                    name=item.Name, metadata=item.Metadata,
                ) for item in body.History
            ),
        )
        run = (await execute_agent.execute(command)).run
        return ok({
            "runId": run.run_id,
            "traceId": run.trace_id,
            "sessionId": run.session_id,
            "action": run.action,
            "replyText": run.output,
            "agentKey": run.target.agent_key,
            "agentVersion": int(run.target.agent_version) if run.target.agent_version else None,
            "toolEvents": [],
            "usage": run.usage.__dict__ if run.usage else None,
            "error": run.error.__dict__ if run.error else None,
        })
    except (AgentNotFoundError, LookupError):
        return JSONResponse(
            {"success": False, "msg": f"Agent '{agent_key}' not found or not published", "data": None},
            status_code=404,
        )


@router.post("/agents/{agent_key}/turn/stream")
async def agent_turn_stream(
    agent_key: str,
    body: AgentTurnRequest,
    execute_agent: ExecuteAgentDep,
    current_user: CurrentUser,
):
    try:
        command = ExecuteAgentCommand(
            agent_key=agent_key, input=body.Message, session_id=body.SessionId,
            user_id=body.UserId or current_user["user_id"],
            history=tuple(
                AgentMessage(
                    role=AgentRole(item.Role.lower()), content=item.Content,
                    name=item.Name, metadata=item.Metadata,
                ) for item in body.History
            ),
        )
        generator = run_execute_agent_stream(
            execute_agent, command, session_factory=get_session_factory(),
        )
        return StreamingResponse(generator, media_type="text/event-stream")
    except (AgentNotFoundError, LookupError):
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
