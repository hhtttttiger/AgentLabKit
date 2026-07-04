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
    from config import Settings
    return Settings(
        debug=True,
        jwt_secret_key="test-secret-key-do-not-use-in-production",
        jwt_expires_minutes=60,
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
    from main import create_app
    return create_app(settings)


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
