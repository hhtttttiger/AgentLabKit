"""Characterization tests for files endpoints — verify API contract survives refactor."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_upload_and_list_file(client, auth_headers):
    """Upload a file, then list to confirm it appears."""
    resp = await client.post(
        "/api/files",
        files={"file": ("hello.txt", b"hello world", "text/plain")},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    uploaded = data["data"]
    assert uploaded["fileName"] == "hello.txt"
    assert uploaded["contentType"] == "text/plain"
    assert uploaded["sizeBytes"] == 11
    assert uploaded["storageType"] == "local"
    assert "id" in uploaded
    assert "storagePath" in uploaded
    assert "createdAtUtc" in uploaded

    # List
    resp = await client.get("/api/files", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["totalCount"] >= 1
    assert any(f["id"] == uploaded["id"] for f in data["data"]["items"])


async def test_list_files_pagination(client, auth_headers):
    """List files with pagination params."""
    resp = await client.get("/api/files?page=1&pageSize=5", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    paginated = data["data"]
    assert "items" in paginated
    assert "totalCount" in paginated
    assert paginated["page"] == 1
    assert paginated["pageSize"] == 5


async def test_get_file_by_id(client, auth_headers):
    """Upload then fetch by ID."""
    resp = await client.post(
        "/api/files",
        files={"file": ("get_test.txt", b"content for get", "text/plain")},
        headers=auth_headers,
    )
    file_id = resp.json()["data"]["id"]

    resp = await client.get(f"/api/files/{file_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["fileName"] == "get_test.txt"
    assert data["data"]["sizeBytes"] == 15


async def test_get_file_not_found(client, auth_headers):
    """Requesting a non-existent file ID returns failure."""
    resp = await client.get("/api/files/999999", headers=auth_headers)
    assert resp.status_code != 200


async def test_delete_file(client, auth_headers):
    """Upload then delete, then verify it's gone."""
    resp = await client.post(
        "/api/files",
        files={"file": ("delete_me.txt", b"temporary", "text/plain")},
        headers=auth_headers,
    )
    file_id = resp.json()["data"]["id"]

    resp = await client.delete(f"/api/files/{file_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Confirm gone
    resp = await client.get(f"/api/files/{file_id}", headers=auth_headers)
    assert resp.status_code != 200


async def test_delete_file_not_found(client, auth_headers):
    """Deleting a non-existent file ID returns failure."""
    resp = await client.delete("/api/files/999999", headers=auth_headers)
    assert resp.status_code != 200
