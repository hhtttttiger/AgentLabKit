"""Auth endpoint tests — login, token validation, health check."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_health_endpoint(client):
    """Health endpoint should be accessible without auth."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["status"] == "healthy"


async def test_login_endpoint_accessible_without_token(client):
    """Login endpoint should not require auth (it issues tokens)."""
    resp = await client.post("/api/auth/token", json={"username": "admin", "password": "wrong"})
    # Should not be 401 — it should attempt login (and fail with wrong password, but not 401)
    assert resp.status_code != 401


async def test_valid_token_accepted(client, auth_headers):
    """A request with a valid token should not get 401 on protected routes."""
    # We test against /api/agents which requires auth
    # Without DB it will fail with 500 (no session), but NOT 401
    resp = await client.get("/api/agents", headers=auth_headers)
    assert resp.status_code != 401


async def test_no_token_rejected(client):
    """A request without a token should get 401 on protected routes."""
    resp = await client.get("/api/agents")
    assert resp.status_code == 401


async def test_expired_token_rejected(client, expired_headers):
    """A request with an expired token should get 401."""
    resp = await client.get("/api/agents", headers=expired_headers)
    assert resp.status_code == 401


async def test_invalid_token_rejected(client):
    """A request with an invalid token should get 401."""
    resp = await client.get("/api/agents", headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401


async def test_malformed_auth_header_rejected(client):
    """A request with malformed Authorization header should get 401."""
    resp = await client.get("/api/agents", headers={"Authorization": "NotBearer token"})
    assert resp.status_code == 401
