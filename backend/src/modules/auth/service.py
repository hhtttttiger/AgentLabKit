from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import BusinessError
from config import Settings
from .models import AuthUser

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

hash_password = _pwd_ctx.hash
verify_password = _pwd_ctx.verify


def _create_token(user: AuthUser, settings: Settings) -> dict:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "username": user.username,
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

    return _create_token(user, settings)


async def list_active_users(session: AsyncSession) -> list[dict]:
    """返回活跃用户列表（供预算 scopeKey 下拉等场景）。密码 hash 不暴露。"""
    result = await session.execute(
        select(AuthUser).where(AuthUser.is_active == True).order_by(AuthUser.username)
    )
    return [
        {"value": u.username, "label": u.display_name or u.username}
        for u in result.scalars().all()
    ]


async def seed_default_user(session: AsyncSession) -> None:
    result = await session.execute(select(AuthUser).where(AuthUser.username == "admin"))
    if result.scalar_one_or_none() is not None:
        return
    session.add(AuthUser(
        username="admin",
        password_hash=hash_password("admin"),
        display_name="Administrator",
    ))
    await session.flush()
