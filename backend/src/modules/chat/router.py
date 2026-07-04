from __future__ import annotations

from fastapi import APIRouter, Query

from common.auth import CurrentUser
from common.response import ok, paged

from .dependencies import ChatSessionServiceDep
from .schemas import (
    ChatMessageResponse,
    ChatSessionResponse,
    CreateSessionRequest,
    SaveTurnRequest,
    UpdateSessionRequest,
)

router = APIRouter()


def _to_session_response(r) -> dict:
    return ChatSessionResponse(
        id=r.id,
        user_id=r.user_id,
        title=r.title,
        model_type=r.model_type,
        model_id=r.model_id,
        message_count=r.message_count,
        created_at_utc=r.created_at_utc,
        updated_at_utc=r.updated_at_utc,
    ).model_dump()


def _to_message_response(r) -> dict:
    return ChatMessageResponse(
        id=r.id,
        session_id=r.session_id,
        role=r.role,
        content=r.content,
        status=r.status,
        error_message=r.error_message,
        trace_json=r.trace_json,
        created_at_utc=r.created_at_utc,
    ).model_dump()


@router.get("/sessions")
async def list_sessions(
    service: ChatSessionServiceDep,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=100),
):
    sessions, total = await service.list_sessions(
        current_user["user_id"], page=page, page_size=pageSize,
    )
    items = [_to_session_response(s) for s in sessions]
    return ok(paged(items, total, page, pageSize))


@router.post("/sessions")
async def create_session(
    body: CreateSessionRequest,
    service: ChatSessionServiceDep,
    current_user: CurrentUser,
):
    session = await service.create_session(current_user["user_id"], body)
    return ok(_to_session_response(session))


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: int,
    service: ChatSessionServiceDep,
    current_user: CurrentUser,
):
    session = await service.get_session(session_id, current_user["user_id"])
    return ok(_to_session_response(session))


@router.patch("/sessions/{session_id}")
async def update_session(
    session_id: int,
    body: UpdateSessionRequest,
    service: ChatSessionServiceDep,
    current_user: CurrentUser,
):
    session = await service.update_session(session_id, current_user["user_id"], body)
    return ok(_to_session_response(session))


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    service: ChatSessionServiceDep,
    current_user: CurrentUser,
):
    await service.delete_session(session_id, current_user["user_id"])
    return ok(None)


@router.get("/sessions/{session_id}/messages")
async def list_messages(
    session_id: int,
    service: ChatSessionServiceDep,
    current_user: CurrentUser,
    cursor: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    messages, has_more = await service.list_messages(
        session_id, current_user["user_id"], cursor=cursor, limit=limit,
    )
    return ok({
        "messages": [_to_message_response(m) for m in messages],
        "hasMore": has_more,
    })


@router.post("/sessions/{session_id}/messages/save-turn")
async def save_turn(
    session_id: int,
    body: SaveTurnRequest,
    service: ChatSessionServiceDep,
    current_user: CurrentUser,
):
    result = await service.save_turn(session_id, current_user["user_id"], body)
    return ok(result.model_dump())
