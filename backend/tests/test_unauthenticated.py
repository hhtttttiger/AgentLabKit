"""Verify all protected routes return 401 without authentication."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio

# All protected route prefixes (everything except /api/auth and /health)
PROTECTED_ROUTES = [
    ("GET", "/api/agents"),
    ("GET", "/api/llm-catalog/connection-profiles"),
    ("GET", "/api/knowledge-bases"),
    ("GET", "/api/files"),
    ("GET", "/api/glossary/categories"),
    ("GET", "/api/cost/overview"),
    ("GET", "/api/traces"),
    ("GET", "/api/memories?userId=test"),
    ("GET", "/api/eval/datasets"),
    ("POST", "/api/chat/complete"),
    ("POST", "/api/ai/invoke/agents/test/turn"),
]


@pytest.mark.parametrize("method,path", PROTECTED_ROUTES)
async def test_protected_route_requires_auth(client, method, path):
    """Every protected route must return 401 when no token is provided."""
    resp = await getattr(client, method.lower())(path)
    assert resp.status_code == 401, f"{method} {path} should require auth, got {resp.status_code}"


async def test_login_not_protected(client):
    """Login endpoint should NOT return 401."""
    resp = await client.post("/api/auth/token", json={"username": "x", "password": "y"})
    assert resp.status_code != 401


async def test_health_not_protected(client):
    """Health endpoint should NOT return 401."""
    resp = await client.get("/health")
    assert resp.status_code == 200
