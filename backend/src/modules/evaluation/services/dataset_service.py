"""Dataset and case management."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import NotFoundError
from evaluation.contracts_v2 import DatasetExample
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

    async def create_example(
        self,
        *,
        dataset_id: str,
        input_text,
        expected_output=None,
        metadata: dict | None = None,
        source_run_id: str,
        source_trace_id: str | None = None,
    ) -> DatasetExample:
        """Create one DatasetExample and let the database own its identity."""
        result = await self._db.execute(
            select(EvalDataset).where(EvalDataset.id == int(dataset_id), EvalDataset.is_active == True)
        )
        dataset = result.scalar_one_or_none()
        if dataset is None:
            raise NotFoundError("Dataset", str(dataset_id))

        case = EvalCase(
            dataset_id=dataset.id,
            case_index=dataset.case_count,
            input_text=input_text,
            expected_output=expected_output,
            metadata_json=dict(metadata or {}),
        )
        self._db.add(case)
        dataset.case_count += 1
        await self._db.flush()
        await self._db.refresh(case)
        return DatasetExample(
            example_id=str(case.id),
            dataset_id=str(case.dataset_id),
            input_text=case.input_text,
            expected_output=case.expected_output,
            context=list(case.context_json or []),
            tags=list(case.tags_json or []),
            metadata=dict(case.metadata_json or {}),
            source_run_id=source_run_id,
            source_trace_id=source_trace_id,
        )

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
