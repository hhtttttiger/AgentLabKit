"""DF-01 regression: fresh admin login must persist a naive-UTC timestamp.

Reproduces the first-run failure: a timezone-aware datetime written into the
``TIMESTAMP WITHOUT TIME ZONE`` ``auth_users.last_login_at_utc`` column raises
TypeError under asyncpg at flush, and a flush-only write is rolled back when
the request session closes.  Durability is asserted from independent sessions
that never shared the writing session's transaction.
"""
from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import select

from config import AuthSettings, Settings
from modules.auth.models import AuthUser
from modules.auth.service import authenticate, seed_default_user

pytestmark = [pytest.mark.asyncio, pytest.mark.db]


def _settings() -> Settings:
    return Settings(
        auth=AuthSettings(
            secret_key="test-secret-key-do-not-use-in-production",
            expires_minutes=30,
        ),
        redis_enabled=False,
        retrieval_enabled=False,
    )


async def _get_admin(session) -> AuthUser:
    result = await session.execute(select(AuthUser).where(AuthUser.username == "admin"))
    return result.scalar_one()


async def test_fresh_admin_first_and_second_login_persist(db_session_factory):
    # Fresh environment: bootstrap seeds the default admin and commits.
    async with db_session_factory() as session:
        await seed_default_user(session)
        await session.commit()

    # First login happens on its own request-scoped session, which closes
    # immediately afterwards (closing a session is not commit).
    async with db_session_factory() as session:
        token = await authenticate(session, "admin", "admin", _settings())
        assert token["accessToken"]
        assert token["tokenType"] == "Bearer"

    # Independent session must observe the durable first-login timestamp.
    async with db_session_factory() as session:
        user = await _get_admin(session)
        first_login = user.last_login_at_utc
        assert first_login is not None, "login write must survive session close"
        assert first_login.tzinfo is None, "column convention is naive UTC"

    await asyncio.sleep(0.01)  # ensure a strictly later microsecond timestamp

    # Second login updates the persisted timestamp.
    async with db_session_factory() as session:
        await authenticate(session, "admin", "admin", _settings())

    async with db_session_factory() as session:
        user = await _get_admin(session)
        assert user.last_login_at_utc is not None
        assert user.last_login_at_utc >= first_login


async def test_failed_login_does_not_touch_last_login(db_session_factory):
    async with db_session_factory() as session:
        await seed_default_user(session)
        await session.commit()

    from common.errors import BusinessError

    async with db_session_factory() as session:
        with pytest.raises(BusinessError):
            await authenticate(session, "admin", "wrong-password", _settings())

    async with db_session_factory() as session:
        user = await _get_admin(session)
        assert user.last_login_at_utc is None
