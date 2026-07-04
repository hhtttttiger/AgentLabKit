"""Dataset and case management."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import NotFoundError
from ..models import EvalDataset, EvalCase


class DatasetService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_datasets(self, *, page: int, page_size: int):
        count_result = await self._db.execute(
            select(func.count(EvalDataset.id)).where(EvalDataset.is_active == True)
        )
        total = count_result.scalar_one()

        offset = (page - 1) * page_size
        result = await self._db.execute(
            select(EvalDataset)
            .where(EvalDataset.is_active == True)
            .order_by(EvalDataset.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = result.scalars().all()
        return [self._to_dataset_view(d) for d in items], total

    async def create_dataset(self, **kwargs) -> dict:
        ds = EvalDataset(**kwargs)
        self._db.add(ds)
        await self._db.flush()
        await self._db.refresh(ds)
        return self._to_dataset_view(ds)

    async def delete_dataset(self, dataset_id: int) -> None:
        result = await self._db.execute(select(EvalDataset).where(EvalDataset.id == dataset_id))
        ds = result.scalar_one_or_none()
        if not ds:
            raise NotFoundError("Dataset", str(dataset_id))
        ds.is_active = False
        await self._db.flush()

    async def list_cases(self, dataset_id: int) -> list[dict]:
        result = await self._db.execute(
            select(EvalCase).where(EvalCase.dataset_id == dataset_id).order_by(EvalCase.case_index)
        )
        return [self._to_case_view(c) for c in result.scalars().all()]

    async def create_cases(self, dataset_id: int, cases: list[dict]) -> dict:
        result = await self._db.execute(select(EvalDataset).where(EvalDataset.id == dataset_id))
        ds = result.scalar_one_or_none()
        if not ds:
            raise NotFoundError("Dataset", str(dataset_id))

        start_idx = ds.case_count
        for i, c in enumerate(cases):
            case = EvalCase(
                dataset_id=dataset_id,
                case_index=start_idx + i,
                input_text=c["input_text"],
                expected_output=c.get("expected_output"),
                context_json=c.get("context", []),
                tags_json=c.get("tags", []),
            )
            self._db.add(case)
        ds.case_count = start_idx + len(cases)
        await self._db.flush()
        return {"added": len(cases), "total": ds.case_count}

    async def delete_case(self, dataset_id: int, case_id: int) -> None:
        result = await self._db.execute(
            select(EvalCase).where(EvalCase.id == case_id, EvalCase.dataset_id == dataset_id)
        )
        case = result.scalar_one_or_none()
        if not case:
            raise NotFoundError("Case", str(case_id))

        ds_result = await self._db.execute(select(EvalDataset).where(EvalDataset.id == dataset_id))
        ds = ds_result.scalar_one_or_none()
        if ds:
            ds.case_count = max(0, ds.case_count - 1)

        await self._db.delete(case)
        await self._db.flush()

    @staticmethod
    def _to_dataset_view(d) -> dict:
        return {
            "id": d.id, "name": d.name, "description": d.description,
            "tags": d.tags_json or [], "case_count": d.case_count,
            "is_active": d.is_active, "created_at_utc": d.created_at_utc,
            "updated_at_utc": d.updated_at_utc,
        }

    @staticmethod
    def _to_case_view(c) -> dict:
        return {
            "id": c.id, "dataset_id": c.dataset_id, "case_index": c.case_index,
            "input_text": c.input_text, "expected_output": c.expected_output,
            "context": c.context_json or [], "tags": c.tags_json or [],
        }
