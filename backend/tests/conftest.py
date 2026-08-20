"""Shared test fixtures for backend integration tests.

Requires a running PostgreSQL instance.  Set env vars:
    APP_DB_HOST, APP_DB_PORT, APP_DB_USER, APP_DB_PASSWORD, APP_DB_NAME

Or use the default localhost/postgres values.
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

import jwt
import pytest

# Ensure src/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# ── Settings override ──────────────────────────────────────────────

@pytest.fixture(scope="session")
def settings():
    """Create settings with test-friendly defaults."""
    from config import AuthSettings, Settings
    return Settings(
        debug=True,
        auth=AuthSettings(
            secret_key="test-secret-key-do-not-use-in-production",
            expires_minutes=60,
        ),
        redis_enabled=False,
        retrieval_enabled=False,
    )


# ── JWT token helpers ──────────────────────────────────────────────

@pytest.fixture(scope="session")
def make_token(settings):
    """Factory fixture that creates valid JWT tokens."""
    def _make(user_id: str = "test-user", username: str = "testuser", expired: bool = False):
        now = datetime.now(timezone.utc)
        exp = now - timedelta(minutes=5) if expired else now + timedelta(minutes=settings.jwt_expires_minutes)
        payload = {
            "sub": user_id,
            "username": username,
            "exp": exp,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return _make


@pytest.fixture(scope="session")
def auth_headers(make_token):
    """Valid Authorization headers for authenticated requests."""
    token = make_token()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def expired_headers(make_token):
    """Authorization headers with an expired token."""
    token = make_token(expired=True)
    return {"Authorization": f"Bearer {token}"}


# ── App fixture ────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def app(settings):
    """Create a FastAPI app with test settings (no lifespan — no DB/Redis)."""
    from unittest.mock import patch

    from fastapi import HTTPException, status

    from common.auth import configure_auth
    from common.dependencies import get_db
    from main import create_app

    # configure_auth is normally called inside lifespan, but we skip lifespan
    # in tests (no DB/Redis).  Call it manually so auth middleware works.
    configure_auth(settings)

    # Patch get_session_factory so services that call it directly (e.g.
    # ChatSessionService) don't crash with RuntimeError.
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock

    @asynccontextmanager
    async def _mock_session_ctx():
        yield AsyncMock()

    _sf_patcher = patch("alkit_db.engine.get_session_factory")
    _mock_get_sf = _sf_patcher.start()
    _mock_get_sf.return_value = _mock_session_ctx

    application = create_app(settings)

    # Override DB dependency: raise 503 instead of crashing with RuntimeError.
    # Tests that need real DB should use @pytest.mark.db and provide a DB.
    async def _no_db():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not available in test environment",
        )
        yield  # pragma: no cover — make this an async generator

    application.dependency_overrides[get_db] = _no_db

    return application


@pytest.fixture
def client(app):
    """Async HTTP test client."""
    from httpx import ASGITransport, AsyncClient
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ── Event loop for async tests ─────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
