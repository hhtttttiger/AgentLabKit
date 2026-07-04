from __future__ import annotations

from fastapi import APIRouter, Depends

from common.auth import require_auth
from common.dependencies import DbSession
from common.response import ok
from config import Settings
from .schemas import LoginRequest
from .service import authenticate, list_active_users

router = APIRouter()


@router.post("/token")
async def login(body: LoginRequest, db: DbSession):
    token = await authenticate(db, body.username, body.password, Settings())
    return ok(token)


@router.get("/users", dependencies=[Depends(require_auth)])
async def list_users(db: DbSession):
    """列出所有活跃用户。"""
    users = await list_active_users(db)
    return ok(users)
