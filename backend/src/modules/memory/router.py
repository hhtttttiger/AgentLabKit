"""长期记忆 API Router — 记忆列表、详情、搜索、统计、整合。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from common.auth import CurrentUser
from common.response import ok, paged
from memory.contracts import MemoryType as MemoryTypeEnum
from .dependencies import MemoryModuleDep
from .schemas import MemoryItem, MemoryStatsResponse, MemorySearchRequest, ConsolidateRequest

router = APIRouter()


def _to_memory_item(r) -> dict:
    return MemoryItem(
        id=r.id,
        user_id=r.user_id,
        session_id=r.session_id,
        memory_type=r.memory_type.value,
        content=r.content,
        summary=r.summary,
        relevance_score=r.relevance_score,
        access_count=r.access_count,
        is_active=r.is_active,
        created_at_utc=r.created_at_utc,
        updated_at_utc=r.updated_at_utc,
    ).model_dump()


@router.get("")
async def list_memories(
    mod: MemoryModuleDep,
    current_user: CurrentUser,
    memoryType: MemoryTypeEnum | None = Query(None, alias="memoryType"),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
):
    records, total = await mod.store.list_by_user(
        current_user["user_id"], memory_type=memoryType, page=page, page_size=pageSize,
    )
    items = [_to_memory_item(r) for r in records]
    return ok(paged(items, total, page, pageSize))


@router.get("/stats")
async def memory_stats(
    mod: MemoryModuleDep,
    current_user: CurrentUser,
):
    user_id = current_user["user_id"]
    counts = await mod.store.count_by_type(user_id)
    total = sum(counts.values())
    return ok(MemoryStatsResponse(user_id=user_id, counts_by_type=counts, total_active=total).model_dump())


@router.post("/search")
async def search_memories(
    body: MemorySearchRequest,
    mod: MemoryModuleDep,
    current_user: CurrentUser,
):
    types = [MemoryTypeEnum(t) for t in body.memory_types] if body.memory_types else None
    memories = await mod.retriever.retrieve(
        query=body.query,
        user_id=current_user["user_id"],
        memory_types=types,
        top_k=body.top_k,
    )
    return ok([_to_memory_item(m) for m in memories])


@router.post("/consolidate")
async def consolidate_memories(
    body: ConsolidateRequest,
    mod: MemoryModuleDep,
    current_user: CurrentUser,
):
    count = await mod.consolidator.consolidate(
        user_id=current_user["user_id"],
        memory_type=MemoryTypeEnum(body.memory_type),
        batch_size=body.batch_size,
    )
    return ok({"consolidatedCount": count})


@router.patch("/{memory_id}")
async def deactivate_memory(
    memory_id: int,
    mod: MemoryModuleDep,
):
    """Soft-deactivate: sets is_active=false, data preserved."""
    updated = await mod.store.deactivate(memory_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory {memory_id} not found or already deactivated",
        )
    return ok(None)


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: int,
    mod: MemoryModuleDep,
):
    """Hard-delete: physically removes record + embedding (FK CASCADE)."""
    deleted = await mod.store.delete(memory_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory {memory_id} not found",
        )
    from fastapi.responses import Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)
