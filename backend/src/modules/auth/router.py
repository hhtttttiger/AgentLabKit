from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from common.auth import CurrentUser, require_auth, require_role
from common.dependencies import DbSession
from common.response import ok, paged
from config import Settings
from .schemas import (
    ChangePasswordRequest,
    LoginRequest,
    UpdateProfileRequest,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from .service import (
    authenticate,
    change_password,
    create_user,
    get_user,
    list_active_users,
    list_users,
    update_profile,
    update_user,
)

router = APIRouter()


# ── Public ────────────────────────────────────────────────────────────


@router.post("/token")
async def login(body: LoginRequest, db: DbSession):
    token = await authenticate(db, body.username, body.password, Settings())
    return ok(token)


# ── Current user ──────────────────────────────────────────────────────


@router.get("/me")
async def get_me(db: DbSession, current_user: CurrentUser):
    user = await get_user(db, int(current_user["user_id"]))
    return ok(UserResponse.model_validate(user).model_dump())


@router.put("/password")
async def change_my_password(body: ChangePasswordRequest, db: DbSession, current_user: CurrentUser):
    await change_password(
        db,
        int(current_user["user_id"]),
        old_password=body.old_password,
        new_password=body.new_password,
    )
    return ok({"message": "Password changed successfully"})


@router.put("/profile")
async def update_my_profile(body: UpdateProfileRequest, db: DbSession, current_user: CurrentUser):
    user = await update_profile(
        db,
        int(current_user["user_id"]),
        display_name=body.display_name,
        email=body.email,
    )
    return ok(UserResponse.model_validate(user).model_dump())


# ── User management (admin only) ─────────────────────────────────────


@router.get("/users", dependencies=[Depends(require_auth)])
async def list_all_users(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """列出所有用户（分页）。"""
    items, total = await list_users(db, page=page, page_size=page_size)
    return ok(paged(
        [UserResponse.model_validate(u).model_dump() for u in items],
        total,
        page,
        page_size,
    ))


@router.post("/register", dependencies=[Depends(require_role("admin"))])
async def register_user(body: UserCreate, db: DbSession):
    user = await create_user(
        db,
        username=body.username,
        password=body.password,
        display_name=body.display_name,
        email=body.email,
        role=body.role,
    )
    return ok(UserResponse.model_validate(user).model_dump())


@router.get("/users/{user_id}", dependencies=[Depends(require_auth)])
async def get_user_by_id(user_id: int, db: DbSession):
    user = await get_user(db, user_id)
    return ok(UserResponse.model_validate(user).model_dump())


@router.put("/users/{user_id}", dependencies=[Depends(require_role("admin"))])
async def update_user_by_id(user_id: int, body: UserUpdate, db: DbSession):
    user = await update_user(
        db,
        user_id,
        display_name=body.display_name,
        email=body.email,
        role=body.role,
        is_active=body.is_active,
    )
    return ok(UserResponse.model_validate(user).model_dump())


@router.delete("/users/{user_id}", dependencies=[Depends(require_role("admin"))])
async def deactivate_user(user_id: int, db: DbSession):
    user = await update_user(db, user_id, is_active=False)
    return ok(UserResponse.model_validate(user).model_dump())
