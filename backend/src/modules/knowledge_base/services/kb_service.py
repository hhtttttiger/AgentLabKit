"""KnowledgeBaseService — 知识库 CRUD + 文件夹管理。"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.crud import create_entity, get_entity
from common.errors import NotFoundError
from ..models import (
    KnowledgeBaseEntity,
    KnowledgeDocument,
    KnowledgeFolder,
    KbStatus,
)
from ..schemas import (
    KbCreateRequest,
    KbUpdateRequest,
    FolderCreateRequest,
    FolderUpdateRequest,
    KbView,
    KbFolderView,
)

_MAX_FOLDER_DEPTH = 5


class KnowledgeBaseService:

    def __init__(self, db: AsyncSession):
        self._db = db

    # ── Knowledge Base CRUD ────────────────────────────────────────

    async def list_kbs(
        self, page: int, page_size: int, keyword: str | None = None, status: str | None = None,
    ) -> tuple[list[KbView], int]:
        from common.crud import list_entities

        filters: dict = {}
        if keyword:
            # keyword 走 ilike，不能直接用 list_entities 的 eq 过滤
            pass

        query = select(KnowledgeBaseEntity).order_by(KnowledgeBaseEntity.id.desc())
        count_q = select(func.count()).select_from(KnowledgeBaseEntity)
        if keyword:
            query = query.where(KnowledgeBaseEntity.name.ilike(f"%{keyword}%"))
            count_q = count_q.where(KnowledgeBaseEntity.name.ilike(f"%{keyword}%"))
        if status:
            # 前端传 PascalCase (Active/Disabled)，转小写匹配数据库
            query = query.where(KnowledgeBaseEntity.status == status.lower())
            count_q = count_q.where(KnowledgeBaseEntity.status == status.lower())

        total = (await self._db.execute(count_q)).scalar() or 0
        items = (
            await self._db.execute(query.offset((page - 1) * page_size).limit(page_size))
        ).scalars().all()

        # 批量获取文档数
        kb_ids = [kb.id for kb in items]
        count_map = await self._batch_doc_counts(kb_ids)

        views = [self._to_kb_view(kb, count_map.get(kb.id, 0)) for kb in items]
        return views, total

    async def get_kb(self, kb_id: int) -> KbView:
        kb = await get_entity(self._db, KnowledgeBaseEntity, kb_id)
        doc_count = await self._get_doc_count(kb_id)
        return self._to_kb_view(kb, doc_count)

    async def create_kb(self, req: KbCreateRequest) -> KbView:
        config = {}
        if req.settings_json:
            import json
            config = json.loads(req.settings_json)

        kb = await create_entity(
            self._db,
            KnowledgeBaseEntity,
            name=req.name,
            description=req.description,
            config_json=config,
        )
        await self._db.commit()
        return self._to_kb_view(kb, 0)

    async def update_kb(self, kb_id: int, req: KbUpdateRequest) -> KbView:
        kb = await get_entity(self._db, KnowledgeBaseEntity, kb_id)
        if req.name is not None:
            kb.name = req.name
        if req.description is not None:
            kb.description = req.description
        if req.settings_json is not None:
            import json
            kb.config_json = json.loads(req.settings_json)
        await self._db.commit()
        doc_count = await self._get_doc_count(kb_id)
        return self._to_kb_view(kb, doc_count)

    async def delete_kb(self, kb_id: int) -> None:
        """删除知识库 — FK CASCADE 自动清理子表。"""
        kb = await get_entity(self._db, KnowledgeBaseEntity, kb_id)
        await self._db.delete(kb)
        await self._db.commit()

    # ── Folders ────────────────────────────────────────────────────

    async def list_folders(self, kb_id: int) -> list[KbFolderView]:
        await self._ensure_kb(kb_id)
        result = await self._db.execute(
            select(KnowledgeFolder)
            .where(KnowledgeFolder.knowledge_base_id == kb_id)
            .order_by(KnowledgeFolder.sort_order)
        )
        return [self._to_folder_view(f) for f in result.scalars().all()]

    async def create_folder(self, kb_id: int, req: FolderCreateRequest) -> KbFolderView:
        await self._ensure_kb(kb_id)
        parent_id = int(req.parent_folder_id) if req.parent_folder_id else None
        if parent_id is not None:
            await self._validate_folder_depth(parent_id)
        folder = await create_entity(
            self._db,
            KnowledgeFolder,
            knowledge_base_id=kb_id,
            parent_id=parent_id,
            name=req.name,
            sort_order=req.sort_order,
        )
        await self._db.commit()
        return self._to_folder_view(folder)

    async def update_folder(
        self, kb_id: int, folder_id: int, req: FolderUpdateRequest,
    ) -> KbFolderView:
        folder = await self._get_folder(kb_id, folder_id)
        if req.name is not None:
            folder.name = req.name
        if req.sort_order is not None:
            folder.sort_order = req.sort_order
        await self._db.commit()
        return self._to_folder_view(folder)

    async def delete_folder(self, kb_id: int, folder_id: int) -> None:
        """删除文件夹 — 该文件夹下的文档 folder_id 被 SET NULL，移至根目录。"""
        folder = await self._get_folder(kb_id, folder_id)
        # 将该文件夹下的文档移至根目录
        await self._db.execute(
            KnowledgeDocument.__table__.update()
            .where(KnowledgeDocument.folder_id == folder_id)
            .values(folder_id=None)
        )
        await self._db.delete(folder)
        await self._db.commit()

    async def move_folder(self, kb_id: int, folder_id: int, target_parent_id: int | None) -> None:
        folder = await self._get_folder(kb_id, folder_id)
        if target_parent_id is not None:
            if target_parent_id == folder_id:
                raise ValueError("Cannot move folder into itself")
            await self._validate_folder_depth(target_parent_id)
            # 检查目标是否是自己的后代
            await self._validate_no_descendant(folder_id, target_parent_id)
        folder.parent_id = target_parent_id
        await self._db.commit()

    # ── Helpers ────────────────────────────────────────────────────

    async def _ensure_kb(self, kb_id: int) -> KnowledgeBaseEntity:
        return await get_entity(self._db, KnowledgeBaseEntity, kb_id)

    async def _get_folder(self, kb_id: int, folder_id: int) -> KnowledgeFolder:
        folder = await self._db.get(KnowledgeFolder, folder_id)
        if folder is None or folder.knowledge_base_id != kb_id:
            raise NotFoundError("KnowledgeFolder", str(folder_id))
        return folder

    async def _get_doc_count(self, kb_id: int) -> int:
        result = await self._db.execute(
            select(func.count()).select_from(KnowledgeDocument).where(
                KnowledgeDocument.knowledge_base_id == kb_id,
            )
        )
        return result.scalar() or 0

    async def _batch_doc_counts(self, kb_ids: list[int]) -> dict[int, int]:
        if not kb_ids:
            return {}
        result = await self._db.execute(
            select(KnowledgeDocument.knowledge_base_id, func.count())
            .where(KnowledgeDocument.knowledge_base_id.in_(kb_ids))
            .group_by(KnowledgeDocument.knowledge_base_id)
        )
        return {row[0]: row[1] for row in result.all()}

    async def _validate_folder_depth(self, parent_id: int) -> None:
        """检查文件夹层级不超过最大深度 — 递归 CTE，一次查询获取完整深度。"""
        from sqlalchemy import text

        result = await self._db.execute(
            text("""
                WITH RECURSIVE ancestors AS (
                    SELECT id, parent_id, 1 AS depth
                    FROM knowledge_folders
                    WHERE id = :parent_id
                    UNION ALL
                    SELECT kf.id, kf.parent_id, a.depth + 1
                    FROM knowledge_folders kf
                    JOIN ancestors a ON kf.id = a.parent_id
                )
                SELECT MAX(depth) FROM ancestors
            """),
            {"parent_id": parent_id},
        )
        max_depth = result.scalar() or 0
        # Adding a child under parent_id means child depth = max_depth + 1
        if max_depth >= _MAX_FOLDER_DEPTH:
            raise ValueError(f"Folder depth exceeds maximum ({_MAX_FOLDER_DEPTH})")

    async def _validate_no_descendant(self, folder_id: int, target_id: int) -> None:
        """检查 target_id 不是 folder_id 的后代 — 递归 CTE，一次查询。"""
        from sqlalchemy import text

        if target_id == folder_id:
            raise ValueError("Cannot move folder into itself")

        result = await self._db.execute(
            text("""
                WITH RECURSIVE descendants AS (
                    SELECT id, parent_id
                    FROM knowledge_folders
                    WHERE id = :folder_id
                    UNION ALL
                    SELECT kf.id, kf.parent_id
                    FROM knowledge_folders kf
                    JOIN descendants d ON kf.parent_id = d.id
                )
                SELECT 1 FROM descendants WHERE id = :target_id LIMIT 1
            """),
            {"folder_id": folder_id, "target_id": target_id},
        )
        if result.scalar() is not None:
            raise ValueError("Cannot move folder into its own descendant")

    # ── ORM → Schema mapping ──────────────────────────────────────

    @staticmethod
    def _to_kb_view(kb: KnowledgeBaseEntity, doc_count: int = 0) -> KbView:
        import json as _json
        config_json = _json.dumps(kb.config_json) if kb.config_json else None
        return KbView(
            id=str(kb.id),
            name=kb.name,
            description=kb.description,
            document_count=doc_count,
            status=kb.status,
            settings_json=config_json,
            created_at_utc=kb.created_at_utc.isoformat() if kb.created_at_utc else "",
            updated_at_utc=kb.updated_at_utc.isoformat() if kb.updated_at_utc else None,
        )

    @staticmethod
    def _to_folder_view(f: KnowledgeFolder) -> KbFolderView:
        return KbFolderView(
            id=str(f.id),
            knowledge_base_id=str(f.knowledge_base_id),
            parent_folder_id=str(f.parent_id) if f.parent_id else None,
            name=f.name,
            sort_order=f.sort_order,
            created_at_utc=f.created_at_utc.isoformat() if f.created_at_utc else "",
            updated_at_utc=f.updated_at_utc.isoformat() if f.updated_at_utc else None,
        )
