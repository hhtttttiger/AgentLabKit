"""Chat session API tests — auth, schema validation, CRUD flows."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


# ── Auth checks ───────────────────────────────────────────────────────

async def test_list_sessions_requires_auth(client):
    resp = await client.get("/api/chat/sessions")
    assert resp.status_code == 401


async def test_create_session_requires_auth(client):
    resp = await client.post("/api/chat/sessions", json={
        "title": "Test", "modelType": "model", "modelId": "gpt-4",
    })
    assert resp.status_code == 401


async def test_get_session_requires_auth(client):
    resp = await client.get("/api/chat/sessions/1")
    assert resp.status_code == 401


async def test_delete_session_requires_auth(client):
    resp = await client.delete("/api/chat/sessions/1")
    assert resp.status_code == 401


async def test_list_messages_requires_auth(client):
    resp = await client.get("/api/chat/sessions/1/messages")
    assert resp.status_code == 401


async def test_save_turn_requires_auth(client):
    resp = await client.post("/api/chat/sessions/1/messages/save-turn", json={
        "userMessage": {"role": "user", "content": "hi"},
        "assistantMessage": {"role": "assistant", "content": "hello"},
    })
    assert resp.status_code == 401


# ── Schema validation ─────────────────────────────────────────────────

async def test_create_session_validates_model_type(client, auth_headers):
    """modelType must be 'agent' or 'model'."""
    resp = await client.post("/api/chat/sessions", json={
        "title": "Test", "modelType": "invalid", "modelId": "x",
    }, headers=auth_headers)
    assert resp.status_code == 422


async def test_create_session_missing_required_fields(client, auth_headers):
    resp = await client.post("/api/chat/sessions", json={}, headers=auth_headers)
    assert resp.status_code == 422


# ── Auth acceptance (valid token passes auth, returns non-401) ────────

async def test_list_sessions_accepts_valid_token(client, auth_headers):
    """Valid token should pass auth gate (will fail with 500 due to no DB, not 401)."""
    resp = await client.get("/api/chat/sessions", headers=auth_headers)
    assert resp.status_code != 401


async def test_create_session_accepts_valid_token(client, auth_headers):
    resp = await client.post("/api/chat/sessions", json={
        "title": "Test", "modelType": "model", "modelId": "gpt-4",
    }, headers=auth_headers)
    assert resp.status_code != 401


async def test_delete_session_accepts_valid_token(client, auth_headers):
    resp = await client.delete("/api/chat/sessions/1", headers=auth_headers)
    assert resp.status_code != 401


# ── Expired token ─────────────────────────────────────────────────────

async def test_expired_token_rejected(client, expired_headers):
    resp = await client.get("/api/chat/sessions", headers=expired_headers)
    assert resp.status_code == 401
