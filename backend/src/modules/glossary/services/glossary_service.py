"""GlossaryService — business logic for glossary categories, terms, and KB bindings."""

from __future__ import annotations

import csv
import io

from sqlalchemy import cast, delete, func, or_, select, String
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import NotFoundError
from ..models import GlossaryCategory, GlossaryTerm, KnowledgeBaseGlossaryCategory
from ..schemas import (
    CategoryCreateRequest,
    CategoryUpdateRequest,
    CategoryView,
    KbGlossaryBindingView,
    TermCreateRequest,
    TermUpdateRequest,
    TermView,
)


class GlossaryService:
    def __init__(self, db: AsyncSession):
        self._db = db

    # ── Categories ──────────────────────────────────────────────

    async def list_categories(
        self, *, page: int = 1, page_size: int = 12, search: str | None = None,
    ) -> tuple[list[CategoryView], int]:
        query = select(GlossaryCategory)
        count_q = select(func.count()).select_from(GlossaryCategory)
        if search:
            query = query.where(GlossaryCategory.name.ilike(f"%{search}%"))
            count_q = count_q.where(GlossaryCategory.name.ilike(f"%{search}%"))

        total = (await self._db.execute(count_q)).scalar() or 0
        rows = (
            await self._db.execute(
                query.order_by(GlossaryCategory.id).offset((page - 1) * page_size).limit(page_size)
            )
        ).scalars().all()
        return [_cat_to_view(c) for c in rows], total

    async def get_category(self, category_id: int) -> CategoryView:
        return _cat_to_view(await self._find_category(category_id))

    async def create_category(self, body: CategoryCreateRequest) -> CategoryView:
        cat = GlossaryCategory(name=body.name, description=body.description)
        self._db.add(cat)
        await self._db.flush()
        await self._db.commit()
        return _cat_to_view(cat)

    async def update_category(self, category_id: int, body: CategoryUpdateRequest) -> CategoryView:
        cat = await self._find_category(category_id)
        update_data = body.model_dump(exclude_none=True)
        for k, v in update_data.items():
            setattr(cat, k, v)
        await self._db.commit()
        return _cat_to_view(cat)

    async def delete_category(self, category_id: int) -> None:
        cat = await self._find_category(category_id)
        await self._db.delete(cat)
        await self._db.commit()

    # ── Terms ───────────────────────────────────────────────────

    async def list_terms(
        self,
        *,
        category_id: int | None = None,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
    ) -> tuple[list[TermView], int]:
        query = select(GlossaryTerm)
        count_q = select(func.count()).select_from(GlossaryTerm)
        if category_id is not None:
            query = query.where(GlossaryTerm.category_id == category_id)
            count_q = count_q.where(GlossaryTerm.category_id == category_id)
        if search:
            term_filter = GlossaryTerm.term.ilike(f"%{search}%")
            synonym_filter = cast(GlossaryTerm.synonyms_json, String).ilike(f"%{search}%")
            combined = or_(term_filter, synonym_filter)
            query = query.where(combined)
            count_q = count_q.where(combined)

        total = (await self._db.execute(count_q)).scalar() or 0
        rows = (
            await self._db.execute(
                query.order_by(GlossaryTerm.id).offset((page - 1) * page_size).limit(page_size)
            )
        ).scalars().all()
        return [_term_to_view(t) for t in rows], total

    async def get_term(self, term_id: int) -> TermView:
        t = await self._db.get(GlossaryTerm, term_id)
        if t is None:
            raise NotFoundError("GlossaryTerm", str(term_id))
        return _term_to_view(t)

    async def create_term(self, body: TermCreateRequest) -> TermView:
        await self._find_category(body.category_id)
        t = GlossaryTerm(
            category_id=body.category_id,
            term=body.term,
            synonyms_json=body.synonyms,
        )
        self._db.add(t)
        await self._db.flush()
        await self._db.commit()
        return _term_to_view(t)

    async def update_term(self, term_id: int, body: TermUpdateRequest) -> TermView:
        t = await self._db.get(GlossaryTerm, term_id)
        if t is None:
            raise NotFoundError("GlossaryTerm", str(term_id))
        if body.category_id is not None:
            await self._find_category(body.category_id)
            t.category_id = body.category_id
        if body.term is not None:
            t.term = body.term
        if body.synonyms is not None:
            t.synonyms_json = body.synonyms
        await self._db.commit()
        return _term_to_view(t)

    async def delete_term(self, term_id: int) -> None:
        t = await self._db.get(GlossaryTerm, term_id)
        if t is None:
            raise NotFoundError("GlossaryTerm", str(term_id))
        await self._db.delete(t)
        await self._db.commit()

    async def import_terms(self, content: bytes, filename: str) -> dict:
        """批量导入术语（CSV）。返回 {importedCount, errors}。"""
        filename_lower = (filename or "").lower()
        errors: list[str] = []

        if filename_lower.endswith(".xlsx") or content[:2] == b"PK":
            return {"importedCount": 0, "errors": ["暂不支持 .xlsx 格式，请先另存为 CSV 后再导入。"]}

        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("gbk", errors="replace")

        reader = csv.DictReader(io.StringIO(text))
        fieldnames = {(f or "").strip() for f in (reader.fieldnames or [])}
        if "term" not in fieldnames or "category" not in fieldnames:
            return {
                "importedCount": 0,
                "errors": ["CSV 缺少必需的列：term, category（参考下载的模板）。"],
            }

        category_cache: dict[str, GlossaryCategory] = {}
        imported = 0

        for line_no, row in enumerate(reader, start=2):
            term = (row.get("term") or "").strip()
            category_name = (row.get("category") or "").strip()
            synonyms = _split_synonyms(row.get("synonyms") or "")

            if not term:
                errors.append(f"第 {line_no} 行：term 为空，已跳过。")
                continue
            if not category_name:
                errors.append(f"第 {line_no} 行：category 为空，已跳过。")
                continue

            try:
                category = await self._get_or_create_category(category_cache, category_name)
                self._db.add(GlossaryTerm(
                    category_id=category.id,
                    term=term,
                    synonyms_json=synonyms,
                ))
                imported += 1
            except Exception as exc:
                errors.append(f"第 {line_no} 行：{exc}")

        await self._db.commit()
        return {"importedCount": imported, "errors": errors}

    # ── KB Bindings ─────────────────────────────────────────────

    async def get_kb_glossary_binding(self, kb_id: int) -> KbGlossaryBindingView:
        from sqlalchemy import select as sel

        bindings = (
            await self._db.execute(
                sel(KnowledgeBaseGlossaryCategory)
                .where(KnowledgeBaseGlossaryCategory.knowledge_base_id == kb_id)
                .order_by(KnowledgeBaseGlossaryCategory.id)
            )
        ).scalars().all()

        category_ids = [b.category_id for b in bindings]
        categories: list[CategoryView] = []
        if category_ids:
            rows = (
                await self._db.execute(
                    sel(GlossaryCategory).where(GlossaryCategory.id.in_(category_ids))
                )
            ).scalars().all()
            id_to_cat = {c.id: c for c in rows}
            categories = [_cat_to_view(id_to_cat[cid]) for cid in category_ids if cid in id_to_cat]

        return KbGlossaryBindingView(
            knowledge_base_id=str(kb_id),
            category_ids=[str(cid) for cid in category_ids],
            categories=categories,
        )

    async def replace_kb_glossary_binding(self, kb_id: int, category_ids: list[int]) -> None:
        if category_ids:
            existing = (
                await self._db.execute(
                    select(GlossaryCategory.id).where(GlossaryCategory.id.in_(category_ids))
                )
            ).scalars().all()
            if len(existing) != len(category_ids):
                missing = set(category_ids) - set(existing)
                raise NotFoundError("GlossaryCategory", str(missing.pop()))

        await self._db.execute(
            delete(KnowledgeBaseGlossaryCategory)
            .where(KnowledgeBaseGlossaryCategory.knowledge_base_id == kb_id)
        )
        for cid in category_ids:
            self._db.add(KnowledgeBaseGlossaryCategory(
                knowledge_base_id=kb_id,
                category_id=cid,
            ))
        await self._db.commit()

    # ── Helpers ─────────────────────────────────────────────────

    async def _find_category(self, category_id: int) -> GlossaryCategory:
        cat = await self._db.get(GlossaryCategory, category_id)
        if cat is None:
            raise NotFoundError("GlossaryCategory", str(category_id))
        return cat

    async def _get_or_create_category(
        self, cache: dict[str, GlossaryCategory], name: str
    ) -> GlossaryCategory:
        if name in cache:
            return cache[name]
        existing = (
            await self._db.execute(select(GlossaryCategory).where(GlossaryCategory.name == name))
        ).scalars().first()
        if existing is None:
            existing = GlossaryCategory(name=name)
            self._db.add(existing)
            await self._db.flush()
        cache[name] = existing
        return existing


# ── View mappers ──────────────────────────────────────────────────

def _cat_to_view(c: GlossaryCategory) -> CategoryView:
    return CategoryView(
        id=str(c.id),
        name=c.name,
        description=c.description,
        created_at_utc=c.created_at_utc.isoformat(),
        updated_at_utc=c.updated_at_utc.isoformat() if c.updated_at_utc else None,
    )


def _term_to_view(t: GlossaryTerm) -> TermView:
    return TermView(
        id=str(t.id),
        category_id=str(t.category_id),
        term=t.term,
        synonyms=t.synonyms_json or [],
        created_at_utc=t.created_at_utc.isoformat(),
        updated_at_utc=t.updated_at_utc.isoformat() if t.updated_at_utc else None,
    )


def _split_synonyms(raw: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for part in raw.replace("\n", "|").split("|"):
        item = part.strip()
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out
