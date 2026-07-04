# Extract Business Logic from Routers into Services

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move business logic from `files`, `ai_invoke`, and `evaluation` router layers into dedicated service classes so the web layer becomes a thin shell — replaceable by gRPC/CLI without duplicating logic.

**Architecture:** Follow existing patterns (`RunService`, `ChatSessionService`) — class-based services taking `AsyncSession` in constructor, returning dicts. DI wiring via `dependencies.py` with `Annotated` type aliases. Routers reduce to: parameter extraction → delegate → `ok()`.

**Tech Stack:** FastAPI, SQLAlchemy async, aiofiles, existing `common.response` / `common.errors` / `common.dependencies`

## Global Constraints

- Zero behavior change: existing API contracts, response shapes, and status codes must be preserved
- Follow `RunService` class-based pattern: `__init__(self, db: AsyncSession)`, methods return dicts
- DI wiring via `dependencies.py` + `Annotated[ServiceClass, Depends(get_...)]`
- No new dependencies beyond what's already in the project
- Tests are integration tests via HTTP client (matching existing `tests/conftest.py` pattern)

---

### Task 1: Extract `files` module service layer (P0)

**Files:**
- Create: `backend/src/modules/files/service.py`
- Create: `backend/src/modules/files/dependencies.py`
- Create: `backend/tests/test_files.py`
- Modify: `backend/src/modules/files/router.py`

**Interfaces:**
- Consumes: `DbSession` (from `common.dependencies`), `StoredFile` (from `.models`), `Settings` (from `config`), `aiofiles`, `Path` from pathlib
- Produces: `FileServiceDep` (Annotated alias for DI), `FileService` class with methods below

**`FileService` public API:**
```python
class FileService:
    def __init__(self, db: AsyncSession) -> None

    async def upload(self, *, file_name: str, content_type: str | None,
                     content: bytes) -> dict

    async def list_files(self, *, page: int = 1,
                         page_size: int = 20) -> tuple[list[dict], int]

    async def get_file(self, file_id: int) -> dict   # raises NotFoundError

    async def delete_file(self, file_id: int) -> None  # raises NotFoundError
```

- [ ] **Step 1: Write the characterization test**

Create `backend/tests/test_files.py` — tests that call the existing endpoints and assert responses. These tests MUST pass before and after the refactor, proving zero behavior change.

```python
"""Characterization tests for files endpoints — verify API contract survives refactor."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_upload_and_list_file(client: AsyncClient, auth_headers: dict):
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


async def test_list_files_pagination(client: AsyncClient, auth_headers: dict):
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


async def test_get_file_by_id(client: AsyncClient, auth_headers: dict):
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


async def test_get_file_not_found(client: AsyncClient, auth_headers: dict):
    """Requesting a non-existent file ID returns failure."""
    resp = await client.get("/api/files/999999", headers=auth_headers)
    assert resp.status_code != 200  # NotFoundError maps to 4xx


async def test_delete_file(client: AsyncClient, auth_headers: dict):
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


async def test_delete_file_not_found(client: AsyncClient, auth_headers: dict):
    """Deleting a non-existent file ID returns failure."""
    resp = await client.delete("/api/files/999999", headers=auth_headers)
    assert resp.status_code != 200
```

- [ ] **Step 2: Run tests to verify they fail or are incomplete**

Run: `pytest backend/tests/test_files.py -v`
Expected: Some tests may fail if the `/api/files` route prefix differs. Adjust route paths to match actual app routing, then re-run until tests exercise the real endpoints.

- [ ] **Step 3: Create `backend/src/modules/files/service.py`**

```python
"""File storage service — upload, list, get, delete with local filesystem backend."""
from __future__ import annotations

from pathlib import Path

import aiofiles
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import NotFoundError
from config import Settings
from .models import StoredFile


class FileService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def upload(
        self,
        *,
        file_name: str,
        content_type: str | None,
        content: bytes,
    ) -> dict:
        settings = Settings()
        base = Path(settings.file_storage_local_base_path)
        base.mkdir(parents=True, exist_ok=True)

        storage_path = str(base / (file_name or "untitled"))

        async with aiofiles.open(storage_path, "wb") as f:
            await f.write(content)

        stored = StoredFile(
            file_name=file_name or "untitled",
            content_type=content_type,
            size_bytes=len(content),
            storage_path=storage_path,
        )
        self._db.add(stored)
        await self._db.flush()
        await self._db.commit()
        return self._to_dict(stored)

    async def list_files(
        self, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict], int]:
        query = select(StoredFile).order_by(StoredFile.id.desc())
        total = (
            await self._db.execute(select(func.count()).select_from(StoredFile))
        ).scalar() or 0
        items = (
            await self._db.execute(
                query.offset((page - 1) * page_size).limit(page_size)
            )
        ).scalars().all()
        return [self._to_dict(i) for i in items], total

    async def get_file(self, file_id: int) -> dict:
        f = await self._db.get(StoredFile, file_id)
        if f is None:
            raise NotFoundError("File", str(file_id))
        return self._to_dict(f)

    async def delete_file(self, file_id: int) -> None:
        f = await self._db.get(StoredFile, file_id)
        if f is None:
            raise NotFoundError("File", str(file_id))
        path = Path(f.storage_path)
        if path.exists():
            await aiofiles.os.remove(str(path))
        await self._db.delete(f)
        await self._db.commit()

    @staticmethod
    def _to_dict(f: StoredFile) -> dict:
        return {
            "id": f.id,
            "fileName": f.file_name,
            "contentType": f.content_type,
            "sizeBytes": f.size_bytes,
            "storagePath": f.storage_path,
            "storageType": f.storage_type,
            "createdAtUtc": f.created_at_utc.isoformat() if f.created_at_utc else None,
        }
```

- [ ] **Step 4: Create `backend/src/modules/files/dependencies.py`**

```python
"""DI wiring for files module."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from common.dependencies import DbSession
from .service import FileService


def get_file_service(db: DbSession) -> FileService:
    return FileService(db)


FileServiceDep = Annotated[FileService, Depends(get_file_service)]
```

- [ ] **Step 5: Refactor `backend/src/modules/files/router.py`**

Replace the entire file content. Every endpoint now delegates to `FileServiceDep`. No direct DB queries, no file I/O, no `_to_dict` helper.

```python
from __future__ import annotations

from fastapi import APIRouter, Query, UploadFile, File as FastAPIFile

from common.response import ok, paged
from .dependencies import FileServiceDep

router = APIRouter()


@router.post("")
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    svc: FileServiceDep = ...,
):
    content = await file.read()
    result = await svc.upload(
        file_name=file.filename or "untitled",
        content_type=file.content_type,
        content=content,
    )
    return ok(result)


@router.get("")
async def list_files(
    svc: FileServiceDep,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
):
    items, total = await svc.list_files(page=page, page_size=pageSize)
    return ok(paged(items, total, page, pageSize))


@router.get("/{file_id}")
async def get_file(file_id: int, svc: FileServiceDep):
    return ok(await svc.get_file(file_id))


@router.delete("/{file_id}")
async def delete_file(file_id: int, svc: FileServiceDep):
    await svc.delete_file(file_id)
    return ok(None)
```

- [ ] **Step 6: Run characterization tests to verify zero behavior change**

Run: `pytest backend/tests/test_files.py -v`
Expected: ALL tests pass with the same assertions as Step 1.

- [ ] **Step 7: Commit**

```bash
git add backend/src/modules/files/service.py \
        backend/src/modules/files/dependencies.py \
        backend/src/modules/files/router.py \
        backend/tests/test_files.py
git commit -m "refactor(files): extract FileService from router

Move all DB queries and file I/O from router handlers into FileService
class. Router now only handles parameter extraction and response
serialization.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: Extract `ai_invoke` module service layer (P1)

**Files:**
- Create: `backend/src/modules/ai_invoke/service.py`
- Create: `backend/src/modules/ai_invoke/dependencies.py`
- Modify: `backend/src/modules/ai_invoke/router.py`

**Interfaces:**
- Consumes: `GatewayService` (from `llm_gateway.core.service`), `AgentRuntime`, `BackendAgentDefinitionLoader`, `session_factory` (from `alkit_db.engine`), `AgentDefinition` ORM, `agent_turn` module (existing)
- Produces: `InvokeServiceDep` (Annotated alias), `InvokeService` class

**`InvokeService` public API:**
```python
class InvokeService:
    def __init__(self, *, gateway_service, agent_runtime,
                 agent_definition_loader, session_factory) -> None

    async def list_agent_options(self, db: AsyncSession) -> list[dict]

    async def run_agent_turn(self, *, agent_key: str, message: str,
                             session_id: str | None, user_id: str,
                             history: list[AgentTurnHistoryItem]) -> dict

    def run_agent_turn_stream(self, *, agent_key: str, message: str,
                              session_id: str | None, user_id: str,
                              history: list[AgentTurnHistoryItem]) -> AsyncGenerator

    async def generate_text(self, *, model_id: str, message: str,
                            system_prompt: str | None) -> dict

    async def generate_text_stream(self, *, model_id: str, message: str,
                                   system_prompt: str | None) -> AsyncGenerator

    async def generate_text_test_stream(self, *, model_id: str, message: str,
                                        system_prompt: str | None) -> AsyncGenerator

    async def generate_embedding_test(self, *, model_id: str, text: str,
                                      dimensions: int | None) -> dict
```

- [ ] **Step 1: Create `backend/src/modules/ai_invoke/service.py`**

Extract all business logic from `router.py` into a single service class. The `_resolve_published_snapshot`, `_history_to_messages`, prompt assembly, gateway calls, SSE event generation, timing/diagnostic collection all live here. The router will only handle: parameter extraction → delegate → `ok()` / `StreamingResponse`.

```python
"""Invoke service — agent and model invocation orchestration."""
from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_runtime import AgentMessage, AgentRole
from agent_runtime import AgentTurnRequest as RuntimeTurnRequest
from modules.agent.models import AgentDefinition
from .agent_turn import run_agent_turn_stream, write_audit


class InvokeService:
    def __init__(
        self,
        *,
        gateway_service: Any,
        agent_runtime: Any,
        agent_definition_loader: Any,
        session_factory: Any,
    ) -> None:
        self._gateway = gateway_service
        self._runtime = agent_runtime
        self._loader = agent_definition_loader
        self._session_factory = session_factory

    # ── Agent options ──────────────────────────────────────────────────

    async def list_agent_options(self, db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(AgentDefinition)
            .where(
                AgentDefinition.is_enabled == True,
                AgentDefinition.published_version != None,
            )
            .order_by(AgentDefinition.display_name)
        )
        return [
            {
                "agentKey": a.agent_key,
                "displayName": a.display_name,
                "description": a.description,
                "icon": a.icon,
                "publishedVersionNumber": a.published_version,
            }
            for a in result.scalars().all()
        ]

    # ── Agent turn (sync) ──────────────────────────────────────────────

    async def run_agent_turn(
        self,
        *,
        agent_key: str,
        message: str,
        session_id: str | None,
        user_id: str,
        history: list[dict],
    ) -> dict:
        snapshot = await self._resolve_published_snapshot(agent_key)
        if snapshot is None:
            raise AgentNotFoundError(agent_key)

        agent_history = _history_to_messages(history)
        trace_id = str(uuid.uuid4())
        started_at = time.perf_counter()
        effective_session_id = session_id or str(uuid.uuid4())

        result = await self._runtime.run_turn(
            RuntimeTurnRequest(
                session_id=effective_session_id,
                user_message=message,
                history=agent_history,
                user_id=user_id,
                agent_key=agent_key,
                agent_version=snapshot.version_number,
                trace_id=trace_id,
            )
        )

        await write_audit(
            self._session_factory,
            agent_key=agent_key,
            run_id=trace_id,
            agent_version=snapshot.version_number,
            message=message,
            reply_text=result.reply_text,
            tool_events=list(result.tool_events),
            usage=result.usage,
            status="error" if result.error is not None else "success",
            duration_ms=int((time.perf_counter() - started_at) * 1000),
            error_message=result.error.message if result.error is not None else None,
        )

        return {
            "action": result.action.value if result.action else None,
            "replyText": result.reply_text,
            "handoffReason": result.handoff_reason,
            "agentKey": result.agent_key,
            "agentVersion": result.agent_version,
            "toolEvents": [te.model_dump() for te in result.tool_events],
            "usage": result.usage.model_dump() if result.usage else None,
            "error": result.error.model_dump() if result.error else None,
        }

    # ── Agent turn (stream) ────────────────────────────────────────────

    async def run_agent_turn_stream(
        self,
        *,
        agent_key: str,
        message: str,
        session_id: str | None,
        user_id: str,
        history: list[dict],
    ) -> AsyncGenerator:
        snapshot = await self._resolve_published_snapshot(agent_key)
        if snapshot is None:
            raise AgentNotFoundError(agent_key)

        agent_history = _history_to_messages(history)
        effective_session_id = session_id or str(uuid.uuid4())

        async for event in run_agent_turn_stream(
            self._runtime,
            agent_key=agent_key,
            agent_version=snapshot.version_number,
            message=message,
            session_id=effective_session_id,
            history=agent_history,
            session_factory=self._session_factory,
            user_id=user_id,
        ):
            yield event

    # ── Model text (sync) ──────────────────────────────────────────────

    async def generate_text(
        self,
        *,
        model_id: str,
        message: str,
        system_prompt: str | None = None,
    ) -> dict:
        from llm_gateway.models import TextGenerateRequest

        prompt = self._build_prompt(message, system_prompt)
        llm_request = TextGenerateRequest(model=model_id, prompt=prompt)
        result = await self._gateway.generate_text(llm_request)

        return {
            "content": result.text,
            "model": result.model,
            "provider": result.provider,
            "usage": result.usage.model_dump() if result.usage else None,
        }

    # ── Model text (stream) ────────────────────────────────────────────

    async def generate_text_stream(
        self,
        *,
        model_id: str,
        message: str,
        system_prompt: str | None = None,
    ) -> AsyncGenerator:
        from llm_gateway.models import TextGenerateRequest

        prompt = self._build_prompt(message, system_prompt)
        llm_request = TextGenerateRequest(model=model_id, prompt=prompt)

        try:
            async for event in self._gateway.generate_text_stream(llm_request):
                chunk = {
                    "content": event.delta or "",
                    "done": event.event_type == "finished",
                }
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            error_chunk = {"content": str(e), "done": True}
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    # ── Model text (test-stream with diagnostics) ──────────────────────

    async def generate_text_test_stream(
        self,
        *,
        model_id: str,
        message: str,
        system_prompt: str | None = None,
    ) -> AsyncGenerator:
        from llm_gateway.models import TextGenerateRequest

        prompt = self._build_prompt(message, system_prompt)
        llm_request = TextGenerateRequest(model=model_id, prompt=prompt)

        started_at = time.perf_counter()
        ttft_ms: int | None = None
        first_token_recorded = False
        instance_key: str | None = None
        provider_value: str | None = None
        model_value: str | None = None
        finish_reason: str | None = None
        usage = None

        try:
            async for event in self._gateway.generate_text_stream(llm_request):
                if event.instance_key:
                    instance_key = event.instance_key
                if event.provider is not None:
                    provider_value = event.provider.value
                if event.model:
                    model_value = event.model
                if event.usage:
                    usage = event.usage
                if event.finish_reason:
                    finish_reason = event.finish_reason
                if event.delta:
                    if not first_token_recorded:
                        ttft_ms = int((time.perf_counter() - started_at) * 1000)
                        first_token_recorded = True
                    chunk = {
                        "type": "content",
                        "content": event.delta,
                        "instance_key": instance_key,
                        "provider": provider_value,
                        "model": model_value,
                    }
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

            total_ms = int((time.perf_counter() - started_at) * 1000)
            stats = {
                "type": "stats",
                "ttft_ms": ttft_ms,
                "total_ms": total_ms,
                "instance_key": instance_key,
                "provider": provider_value,
                "model": model_value,
                "finish_reason": finish_reason,
                "input_tokens": usage.input_tokens if usage else None,
                "output_tokens": usage.output_tokens if usage else None,
                "total_tokens": usage.total_tokens if usage else None,
            }
            yield f"data: {json.dumps(stats, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            total_ms = int((time.perf_counter() - started_at) * 1000)
            error_payload = {
                "type": "error",
                "message": str(e),
                "code": getattr(getattr(e, "code", None), "value", None),
                "ttft_ms": ttft_ms,
                "total_ms": total_ms,
            }
            yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    # ── Embedding test ─────────────────────────────────────────────────

    async def generate_embedding_test(
        self,
        *,
        model_id: str,
        text: str,
        dimensions: int | None = None,
    ) -> dict:
        from llm_gateway.models import EmbeddingGenerateRequest

        llm_request = EmbeddingGenerateRequest(
            model=model_id,
            input=text,
            dimensions=dimensions,
        )

        started_at = time.perf_counter()
        try:
            result = await self._gateway.generate_embedding(llm_request)
        except Exception as e:
            total_ms = int((time.perf_counter() - started_at) * 1000)
            raise EmbeddingError(
                message=str(e),
                code=getattr(getattr(e, "code", None), "value", None),
                latency_ms=total_ms,
            ) from e

        total_ms = int((time.perf_counter() - started_at) * 1000)
        embedding = result.embedding
        preview = embedding[:10] if len(embedding) > 10 else embedding

        return {
            "success": True,
            "provider": result.provider.value if result.provider else None,
            "model": result.model,
            "dimensions": result.dimensions,
            "vectorPreview": preview,
            "vectorPreviewTruncated": len(embedding) > 10,
            "usage": result.usage.model_dump() if result.usage else None,
            "latencyMs": total_ms,
        }

    # ── Helpers ────────────────────────────────────────────────────────

    async def _resolve_published_snapshot(self, agent_key: str):
        if self._loader is None:
            return None
        return await self._loader.load(agent_key)

    @staticmethod
    def _build_prompt(message: str, system_prompt: str | None) -> str:
        if system_prompt:
            return f"System: {system_prompt}\n\nUser: {message}"
        return message


# ── Domain errors ─────────────────────────────────────────────────────

class AgentNotFoundError(Exception):
    def __init__(self, agent_key: str) -> None:
        self.agent_key = agent_key
        super().__init__(f"Agent '{agent_key}' not found or not published")


class EmbeddingError(Exception):
    def __init__(self, *, message: str, code: str | None, latency_ms: int) -> None:
        self.message = message
        self.code = code
        self.latency_ms = latency_ms
        super().__init__(message)


# ── Shared helpers (moved from router) ─────────────────────────────────

def _history_to_messages(items: list[dict]) -> list[AgentMessage]:
    return [
        AgentMessage(
            role=AgentRole(item["Role"].lower()),
            content=item["Content"],
            name=item.get("Name"),
            metadata=dict(item.get("Metadata") or {}),
        )
        for item in items
    ]
```

- [ ] **Step 2: Create `backend/src/modules/ai_invoke/dependencies.py`**

The DI factory extracts runtime services from `request.app.state` — matching the existing `_get_gateway_service` / `_get_agent_runtime` / `_get_agent_definition_loader` helpers, but consolidated into a single service factory.

```python
"""DI wiring for ai_invoke module."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from alkit_db.engine import get_session_factory
from .service import InvokeService


def get_invoke_service(request: Request) -> InvokeService:
    gateway = getattr(request.app.state, "gateway_service", None)
    if gateway is None:
        raise RuntimeError(
            "GatewayService not initialized. Check gateway_catalog_database_url config."
        )

    runtime = getattr(request.app.state, "agent_runtime", None)
    if runtime is None:
        raise RuntimeError(
            "AgentRuntime not initialized. Check lifespan agent_runtime setup."
        )

    loader = getattr(request.app.state, "agent_definition_loader", None)

    return InvokeService(
        gateway_service=gateway,
        agent_runtime=runtime,
        agent_definition_loader=loader,
        session_factory=get_session_factory(),
    )


InvokeServiceDep = Annotated[InvokeService, Depends(get_invoke_service)]
```

- [ ] **Step 3: Refactor `backend/src/modules/ai_invoke/router.py`**

Replace the entire file. All request models stay (they define the HTTP contract). All business logic moves to `InvokeService`. Router becomes pure delegation.

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from common.auth import CurrentUser
from common.dependencies import DbSession
from common.response import ok
from .dependencies import InvokeServiceDep
from .service import AgentNotFoundError, EmbeddingError

router = APIRouter()


class ModelTextRequest(BaseModel):
    Message: str
    SystemPrompt: str | None = None
    InvocationContext: dict | None = None


class AgentTurnHistoryItem(BaseModel):
    Role: str
    Content: str
    Name: str | None = None
    Metadata: dict[str, str] = {}


class AgentTurnRequest(BaseModel):
    Message: str
    SessionId: str | None = None
    UserId: str | None = None
    History: list[AgentTurnHistoryItem] = []


class ModelEmbeddingTestRequest(BaseModel):
    Text: str
    Dimensions: int | None = None


@router.get("/agents/options")
async def agent_options(db: DbSession, svc: InvokeServiceDep):
    return ok(await svc.list_agent_options(db))


@router.post("/agents/{agent_key}/turn")
async def agent_turn(
    agent_key: str,
    body: AgentTurnRequest,
    svc: InvokeServiceDep,
    current_user: CurrentUser,
):
    try:
        result = await svc.run_agent_turn(
            agent_key=agent_key,
            message=body.Message,
            session_id=body.SessionId,
            user_id=body.UserId or current_user["user_id"],
            history=[h.model_dump() for h in body.History],
        )
        return ok(result)
    except AgentNotFoundError:
        return JSONResponse(
            {"success": False, "msg": f"Agent '{agent_key}' not found or not published", "data": None},
            status_code=404,
        )


@router.post("/agents/{agent_key}/turn/stream")
async def agent_turn_stream(
    agent_key: str,
    body: AgentTurnRequest,
    svc: InvokeServiceDep,
    current_user: CurrentUser,
):
    try:
        generator = svc.run_agent_turn_stream(
            agent_key=agent_key,
            message=body.Message,
            session_id=body.SessionId,
            user_id=body.UserId or current_user["user_id"],
            history=[h.model_dump() for h in body.History],
        )
        return StreamingResponse(generator, media_type="text/event-stream")
    except AgentNotFoundError:
        return JSONResponse(
            {"success": False, "msg": f"Agent '{agent_key}' not found or not published", "data": None},
            status_code=404,
        )


@router.post("/{model_id}/text")
async def model_text(model_id: str, body: ModelTextRequest, svc: InvokeServiceDep):
    result = await svc.generate_text(
        model_id=model_id,
        message=body.Message,
        system_prompt=body.SystemPrompt,
    )
    return ok(result)


@router.post("/{model_id}/text/stream")
async def model_text_stream(model_id: str, body: ModelTextRequest, svc: InvokeServiceDep):
    generator = svc.generate_text_stream(
        model_id=model_id,
        message=body.Message,
        system_prompt=body.SystemPrompt,
    )
    return StreamingResponse(generator, media_type="text/event-stream")


@router.post("/{model_id}/text/test-stream")
async def model_text_test_stream(model_id: str, body: ModelTextRequest, svc: InvokeServiceDep):
    generator = svc.generate_text_test_stream(
        model_id=model_id,
        message=body.Message,
        system_prompt=body.SystemPrompt,
    )
    return StreamingResponse(generator, media_type="text/event-stream")


@router.post("/{model_id}/embedding/test")
async def model_embedding_test(
    model_id: str,
    body: ModelEmbeddingTestRequest,
    svc: InvokeServiceDep,
):
    try:
        result = await svc.generate_embedding_test(
            model_id=model_id,
            text=body.Text,
            dimensions=body.Dimensions,
        )
        return ok(result)
    except EmbeddingError as e:
        return JSONResponse(
            {
                "success": False,
                "error": {"message": e.message, "code": e.code},
                "latencyMs": e.latency_ms,
            },
            status_code=500,
        )
```

- [ ] **Step 4: Verify code imports and structure**

Run: `cd backend && python -c "from src.modules.ai_invoke.service import InvokeService; print('import OK')"`
Expected: No import errors (note: may need running gateway/agent_runtime to fully exercise, but syntax import should succeed).

- [ ] **Step 5: Run existing agent turn tests to verify no regression**

Run: `pytest backend/tests/test_agent_turn.py -v`
Expected: All tests pass (these exercise the `agent_turn.py` module which is NOT being refactored).

- [ ] **Step 6: Commit**

```bash
git add backend/src/modules/ai_invoke/service.py \
        backend/src/modules/ai_invoke/dependencies.py \
        backend/src/modules/ai_invoke/router.py
git commit -m "refactor(ai_invoke): extract InvokeService from router

Move gateway orchestration, SSE streaming, timing/diagnostic collection,
and agent resolution from router handlers into InvokeService class.
Router now only handles HTTP concerns.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: Clean up `evaluation` `trigger_run` orchestration (P2)

**Files:**
- Modify: `backend/src/modules/evaluation/services/run_service.py`
- Modify: `backend/src/modules/evaluation/router.py`

**Interfaces:**
- Consumes: `RunService`, `EvalModuleDep`, `Request.app.state` (for runtime services), `create_target_executor` from `.adapters`
- Produces: Updated `RunService.trigger_run_and_execute` method

**Change:** Move the `create_target_executor` resolution + `background_tasks.add_task` call from `router.py:78-104` into a new `RunService` method. The router becomes a single delegation call.

- [ ] **Step 1: Add `trigger_run_and_execute` to `RunService`**

Add a new method to the existing `RunService` class in `backend/src/modules/evaluation/services/run_service.py`. Append this method before the existing `execute_run` static method (around line 56).

```python
    async def trigger_run_and_execute(
        self,
        config_id: int,
        eval_mod,
        background_tasks,
        request_app_state,
    ) -> dict:
        """Trigger a run and schedule its execution via background tasks.

        Encapsulates the full orchestration: create the run record,
        resolve the TargetExecutor from runtime services, and schedule
        execute_run as a background task.
        """
        run = await self.trigger_run(config_id)

        # Resolve TargetExecutor from run config + runtime services
        from ..adapters import create_target_executor

        run_configs = await self.list_run_configs()
        config = next(
            (c for c in run_configs if str(c["id"]) == str(config_id)), None
        )

        target_executor = None
        if config:
            target_executor = create_target_executor(
                target_type=config["target_type"],
                target_key=config["target_key"],
                agent_runtime=getattr(request_app_state, "agent_runtime", None),
                retrieval_service=getattr(request_app_state, "retrieval_service", None),
                gateway_service=getattr(request_app_state, "gateway_service", None),
            )

        background_tasks.add_task(
            self.execute_run, run["id"], config_id, eval_mod, target_executor
        )
        return run
```

- [ ] **Step 2: Simplify `trigger_run` endpoint in `router.py`**

Replace the `trigger_run` function in `backend/src/modules/evaluation/router.py` (lines 78-104) with a single delegation:

```python
@router.post("/run-configs/{config_id}/run")
async def trigger_run(
    config_id: int,
    svc: RunServiceDep,
    eval_mod: EvalModuleDep,
    background_tasks: BackgroundTasks,
    request: Request,
):
    run = await svc.trigger_run_and_execute(
        config_id=config_id,
        eval_mod=eval_mod,
        background_tasks=background_tasks,
        request_app_state=request.app.state,
    )
    return ok(run)
```

The imports at the top of `router.py` stay the same — `BackgroundTasks` and `Request` are still needed.

- [ ] **Step 3: Verify import integrity**

Run: `cd backend && python -c "from src.modules.evaluation.services.run_service import RunService; print('import OK')"`
Expected: No import errors.

- [ ] **Step 4: Commit**

```bash
git add backend/src/modules/evaluation/services/run_service.py \
        backend/src/modules/evaluation/router.py
git commit -m "refactor(evaluation): move trigger_run orchestration into RunService

Extract TargetExecutor resolution and background task scheduling from
router handler into RunService.trigger_run_and_execute(). Router now
delegates to a single service call.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Verification Checklist

After all three tasks are complete, run the full test suite:

```bash
cd backend
pytest tests/ -v
```

Additionally, verify the architectural invariant — routers no longer import DB/file I/O directly:

```bash
# files router should have no sqlalchemy/aiofiles imports
grep -E "sqlalchemy|aiofiles" backend/src/modules/files/router.py && echo "FAIL: files router still has DB/IO imports" || echo "PASS"

# ai_invoke router should have no gateway/runtime/sqlalchemy imports
grep -E "gateway|sqlalchemy|time\.perf_counter|event_stream" backend/src/modules/ai_invoke/router.py && echo "WARN: check router for remaining business logic" || echo "PASS"

# evaluation router trigger_run should have no create_target_executor
grep "create_target_executor" backend/src/modules/evaluation/router.py && echo "FAIL: evaluation router still has adapter logic" || echo "PASS"
```
