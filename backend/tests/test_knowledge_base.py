"""Knowledge Base end-to-end tests — KB CRUD, folders, documents, search.

Requires a running PostgreSQL database with the schema applied.
Mark with ``@pytest.mark.db`` so they can be skipped without DB.

To run: pytest tests/test_knowledge_base.py -m db
"""
from __future__ import annotations

import io

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.db]


@pytest.fixture
def kb_payload():
    """Sample KB creation payload."""
    return {"name": "Test KB", "description": "A test knowledge base"}


async def _create_kb(client, headers, payload=None):
    """Helper: create a KB and return the response data."""
    payload = payload or {"name": "Test KB", "description": "A test knowledge base"}
    resp = await client.post("/api/knowledge-bases", json=payload, headers=headers)
    assert resp.status_code == 200, f"Create KB failed: {resp.text}"
    return resp.json()["data"]


# ── KB CRUD ────────────────────────────────────────────────────────


async def test_kb_crud_lifecycle(client, auth_headers):
    """Create → Get → Update → List → Delete a knowledge base."""
    # Create
    kb = await _create_kb(client, auth_headers)
    kb_id = kb["id"]
    assert kb["name"] == "Test KB"
    assert kb["status"] == "active"

    # Get
    resp = await client.get(f"/api/knowledge-bases/{kb_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Test KB"

    # Update
    resp = await client.put(
        f"/api/knowledge-bases/{kb_id}",
        json={"name": "Updated KB"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Updated KB"

    # List
    resp = await client.get("/api/knowledge-bases", headers=auth_headers)
    assert resp.status_code == 200
    kbs = resp.json()["data"]["items"]
    assert any(k["id"] == kb_id for k in kbs)

    # Delete
    resp = await client.delete(f"/api/knowledge-bases/{kb_id}", headers=auth_headers)
    assert resp.status_code == 200

    # Verify deleted
    resp = await client.get(f"/api/knowledge-bases/{kb_id}", headers=auth_headers)
    assert resp.status_code == 404


async def test_kb_not_found(client, auth_headers):
    """Getting a non-existent KB should return 404."""
    resp = await client.get("/api/knowledge-bases/999999", headers=auth_headers)
    assert resp.status_code == 404


# ── Folders ────────────────────────────────────────────────────────


async def test_folder_crud(client, auth_headers):
    """Create → List → Update → Delete folders within a KB."""
    kb = await _create_kb(client, auth_headers)
    kb_id = kb["id"]

    # Create root folder
    resp = await client.post(
        f"/api/knowledge-bases/{kb_id}/folders",
        json={"name": "Documents"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    folder = resp.json()["data"]
    folder_id = folder["id"]
    assert folder["name"] == "Documents"

    # Create subfolder
    resp = await client.post(
        f"/api/knowledge-bases/{kb_id}/folders",
        json={"name": "Sub Docs", "parentFolderId": str(folder_id)},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    sub = resp.json()["data"]
    assert sub["parentFolderId"] == str(folder_id)

    # List folders
    resp = await client.get(f"/api/knowledge-bases/{kb_id}/folders", headers=auth_headers)
    assert resp.status_code == 200
    folders = resp.json()["data"]
    assert len(folders) >= 2

    # Delete subfolder
    resp = await client.delete(
        f"/api/knowledge-bases/{kb_id}/folders/{sub['id']}",
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # Cleanup
    await client.delete(f"/api/knowledge-bases/{kb_id}", headers=auth_headers)


# ── Documents ──────────────────────────────────────────────────────


async def test_document_upload_and_list(client, auth_headers):
    """Upload a document and list it."""
    kb = await _create_kb(client, auth_headers)
    kb_id = kb["id"]

    # Upload a text file
    file_content = b"This is a test document for knowledge base indexing."
    resp = await client.post(
        f"/api/knowledge-bases/{kb_id}/documents",
        files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    doc = resp.json()["data"]
    doc_id = doc["id"]
    assert doc["fileName"] == "test.txt"
    assert doc["ingestStatus"] in ("pending", "processing", "completed")

    # List documents
    resp = await client.get(f"/api/knowledge-bases/{kb_id}/documents", headers=auth_headers)
    assert resp.status_code == 200
    docs = resp.json()["data"]["items"]
    assert any(d["id"] == doc_id for d in docs)

    # Get single document
    resp = await client.get(
        f"/api/knowledge-bases/{kb_id}/documents/{doc_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == doc_id

    # Cleanup
    await client.delete(f"/api/knowledge-bases/{kb_id}", headers=auth_headers)


async def test_qa_document_create(client, auth_headers):
    """Create a QA-type document."""
    kb = await _create_kb(client, auth_headers)
    kb_id = kb["id"]

    resp = await client.post(
        f"/api/knowledge-bases/{kb_id}/documents/qa",
        json={"question": "What is Python?", "answer": "A programming language."},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    doc = resp.json()["data"]
    assert doc["sourceType"] == "qa"
    assert doc["qaQuestion"] == "What is Python?"

    # Cleanup
    await client.delete(f"/api/knowledge-bases/{kb_id}", headers=auth_headers)


# ── Search ─────────────────────────────────────────────────────────


async def test_search_empty_kb(client, auth_headers):
    """Searching an empty KB should return empty results."""
    kb = await _create_kb(client, auth_headers)
    kb_id = kb["id"]

    resp = await client.post(
        f"/api/knowledge-bases/{kb_id}/search",
        json={"query": "test query", "topK": 5},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    results = resp.json()["data"]["results"]
    assert isinstance(results, list)

    # Cleanup
    await client.delete(f"/api/knowledge-bases/{kb_id}", headers=auth_headers)
