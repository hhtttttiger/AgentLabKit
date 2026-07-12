from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import BusinessError, ConflictError, NotFoundError
from config import Settings
from .models import AuthUser

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

hash_password = _pwd_ctx.hash
verify_password = _pwd_ctx.verify

_VALID_ROLES = ("admin", "member")


def _create_token(user: AuthUser, settings: Settings) -> dict:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "exp": now + timedelta(minutes=settings.jwt_expires_minutes),
        "iat": now,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return {
        "accessToken": token,
        "expiresIn": settings.jwt_expires_minutes * 60,
        "tokenType": "Bearer",
    }


async def authenticate(
    session: AsyncSession,
    username: str,
    password: str,
    settings: Settings,
) -> dict:
    result = await session.execute(select(AuthUser).where(AuthUser.username == username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.password_hash):
        raise BusinessError("Invalid username or password", status_code=401)

    if not user.is_active:
        raise BusinessError("Account is disabled", status_code=403)

    # Update last login timestamp
    user.last_login_at_utc = datetime.now(timezone.utc)
    await session.flush()

    return _create_token(user, settings)


async def get_user(session: AsyncSession, user_id: int) -> AuthUser:
    user = await session.get(AuthUser, user_id)
    if user is None:
        raise NotFoundError("User", str(user_id))
    return user


async def list_users(
    session: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[AuthUser], int]:
    count_q = select(func.count()).select_from(AuthUser)
    total = (await session.execute(count_q)).scalar() or 0

    query = (
        select(AuthUser)
        .order_by(AuthUser.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await session.execute(query)).scalars().all()
    return list(items), total


async def list_active_users(session: AsyncSession) -> list[dict]:
    """返回活跃用户列表（供预算 scopeKey 下拉等场景）。密码 hash 不暴露。"""
    result = await session.execute(
        select(AuthUser).where(AuthUser.is_active == True).order_by(AuthUser.username)
    )
    return [
        {"value": u.username, "label": u.display_name or u.username}
        for u in result.scalars().all()
    ]


async def create_user(
    session: AsyncSession,
    *,
    username: str,
    password: str,
    display_name: str | None = None,
    email: str | None = None,
    role: str = "member",
) -> AuthUser:
    # Validate role
    if role not in _VALID_ROLES:
        raise BusinessError(f"Invalid role: {role}. Must be one of: {', '.join(_VALID_ROLES)}")

    # Check username uniqueness
    existing = await session.execute(select(AuthUser).where(AuthUser.username == username))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError(f"Username already exists: {username}")

    # Check email uniqueness
    if email:
        existing = await session.execute(select(AuthUser).where(AuthUser.email == email))
        if existing.scalar_one_or_none() is not None:
            raise ConflictError(f"Email already exists: {email}")

    user = AuthUser(
        username=username,
        password_hash=hash_password(password),
        display_name=display_name,
        email=email,
        role=role,
    )
    session.add(user)
    await session.flush()
    return user


async def update_user(
    session: AsyncSession,
    user_id: int,
    *,
    display_name: str | None = None,
    email: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
) -> AuthUser:
    user = await get_user(session, user_id)

    if role is not None:
        if role not in _VALID_ROLES:
            raise BusinessError(f"Invalid role: {role}. Must be one of: {', '.join(_VALID_ROLES)}")
        user.role = role

    if email is not None:
        # Check email uniqueness if changing
        if email != user.email:
            existing = await session.execute(select(AuthUser).where(AuthUser.email == email))
            dup = existing.scalar_one_or_none()
            if dup is not None and dup.id != user_id:
                raise ConflictError(f"Email already exists: {email}")
        user.email = email

    if display_name is not None:
        user.display_name = display_name

    if is_active is not None:
        # Prevent deactivating the last admin
        if not is_active and user.role == "admin":
            admin_count = (
                await session.execute(
                    select(func.count())
                    .select_from(AuthUser)
                    .where(AuthUser.role == "admin", AuthUser.is_active == True)
                )
            ).scalar() or 0
            if admin_count <= 1:
                raise BusinessError("Cannot deactivate the last admin user")
        user.is_active = is_active

    await session.flush()
    return user


async def change_password(
    session: AsyncSession,
    user_id: int,
    *,
    old_password: str,
    new_password: str,
) -> None:
    user = await get_user(session, user_id)

    if not verify_password(old_password, user.password_hash):
        raise BusinessError("Current password is incorrect", status_code=401)

    user.password_hash = hash_password(new_password)
    await session.flush()


async def update_profile(
    session: AsyncSession,
    user_id: int,
    *,
    display_name: str | None = None,
    email: str | None = None,
) -> AuthUser:
    user = await get_user(session, user_id)

    if email is not None and email != user.email:
        existing = await session.execute(select(AuthUser).where(AuthUser.email == email))
        dup = existing.scalar_one_or_none()
        if dup is not None and dup.id != user_id:
            raise ConflictError(f"Email already exists: {email}")
        user.email = email

    if display_name is not None:
        user.display_name = display_name

    await session.flush()
    return user


async def seed_default_user(session: AsyncSession) -> None:
    result = await session.execute(select(AuthUser).where(AuthUser.username == "admin"))
    if result.scalar_one_or_none() is not None:
        return
    session.add(AuthUser(
        username="admin",
        password_hash=hash_password("admin"),
        display_name="Administrator",
        role="admin",
    ))
    await session.flush()
