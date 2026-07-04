"""Agent CRUD + version lifecycle tests.

These tests require a running PostgreSQL database with the schema applied.
Mark with ``@pytest.mark.db`` so they can be skipped in environments without DB.

To run: pytest tests/test_agent_lifecycle.py -m db
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.db]


@pytest.fixture
def agent_data():
    """Sample agent creation payload."""
    return {
        "agentKey": "test-agent",
        "displayName": "Test Agent",
        "description": "An agent for testing",
    }


@pytest.fixture
def version_data():
    """Sample version creation payload (frontend editor contract)."""
    return {
        "systemPromptTemplate": "You are a helpful assistant.",
        "modelKey": "gpt-test",
        "versionLabel": "v1",
        "changeSummary": "initial version",
        "defaultLocale": "en-US",
        "runtimeOptions": {"temperature": 0.7, "maxTokens": 1024},
        "handoffPolicy": {},
        "responsePolicy": {"mode": "default"},
        "guardrailsPolicy": {},
    }


async def test_agent_crud_lifecycle(client, auth_headers, agent_data, version_data):
    """Full lifecycle: create → get → update → create version → publish → disable → delete."""
    # Create agent
    resp = await client.post("/api/agents", json=agent_data, headers=auth_headers)
    assert resp.status_code == 200
    agent = resp.json()["data"]
    assert agent["agentKey"] == "test-agent"
    assert agent["displayName"] == "Test Agent"

    # Get agent
    resp = await client.get("/api/agents/test-agent", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["agentKey"] == "test-agent"

    # Update agent
    resp = await client.put(
        "/api/agents/test-agent",
        json={"displayName": "Updated Agent"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["displayName"] == "Updated Agent"

    # Create version
    resp = await client.post(
        "/api/agents/test-agent/versions",
        json=version_data,
        headers=auth_headers,
    )
    assert resp.status_code == 200
    version = resp.json()["data"]
    assert version["versionNumber"] == 1
    assert version["systemPromptTemplate"] == "You are a helpful assistant."
    assert version["modelKey"] == "gpt-test"
    assert version["versionLabel"] == "v1"
    assert version["defaultLocale"] == "en-US"
    assert version["runtimeOptions"] == {"temperature": 0.7, "maxTokens": 1024}
    assert version["responsePolicy"] == {"mode": "default"}

    # List versions
    resp = await client.get("/api/agents/test-agent/versions", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1

    # Publish agent
    resp = await client.post("/api/agents/test-agent/publish", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["publishedVersion"] == 1

    # Disable agent
    resp = await client.post("/api/agents/test-agent/disable", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["isEnabled"] is False

    # Delete agent
    resp = await client.delete("/api/agents/test-agent", headers=auth_headers)
    assert resp.status_code == 200

    # Verify deleted
    resp = await client.get("/api/agents/test-agent", headers=auth_headers)
    assert resp.status_code == 404


async def test_agent_not_found(client, auth_headers):
    """Getting a non-existent agent should return 404."""
    resp = await client.get("/api/agents/nonexistent", headers=auth_headers)
    assert resp.status_code == 404


async def test_publish_without_versions_fails(client, auth_headers, agent_data):
    """Publishing an agent with no versions should return an error."""
    # Create agent
    await client.post("/api/agents", json=agent_data, headers=auth_headers)

    # Try to publish without versions
    resp = await client.post("/api/agents/test-agent/publish", headers=auth_headers)
    assert resp.status_code == 400  # BusinessError

    # Cleanup
    await client.delete("/api/agents/test-agent", headers=auth_headers)
