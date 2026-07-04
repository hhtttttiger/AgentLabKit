"""MemoryStore — Protocol + PostgresMemoryStore (pgvector)。

DESIGN NOTE: PostgresMemoryStore uses raw SQL (sqlalchemy.text) for full control
over query structure and performance. The ORM models in
backend/src/modules/memory/models.py exist ONLY for Alembic migrations.
Keep column names and types in sync between the raw SQL here and the ORM models.
"""

from __future__ import annotations

import json
from typing import Protocol, runtime_checkable

from sqlalchemy import text as sa_text

from .contracts import MemoryRecord, MemoryType, MemoryQuery


@runtime_checkable
class MemoryStore(Protocol):
    async def save(self, record: MemoryRecord) -> MemoryRecord: ...
    async def save_batch(self, records: list[MemoryRecord]) -> list[MemoryRecord]: ...
    async def get(self, memory_id: int) -> MemoryRecord | None: ...
    async def search(self, query: MemoryQuery, embedding: list[float]) -> list[MemoryRecord]: ...
    async def deactivate(self, memory_id: int) -> bool: ...
    async def delete(self, memory_id: int) -> bool: ...
    async def list_by_user(
        self, user_id: str, memory_type: MemoryType | None = None,
        page: int = 1, page_size: int = 20,
    ) -> tuple[list[MemoryRecord], int]: ...
    async def count_by_type(self, user_id: str) -> dict[str, int]: ...


class PostgresMemoryStore:
    """基于 PostgreSQL + pgvector 的记忆存储。"""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def save(self, record: MemoryRecord) -> MemoryRecord:
        async with self._session_factory() as session:
            result = await session.execute(
                sa_text(
                    "INSERT INTO memory_records "
                    "(user_id, session_id, memory_type, content, summary, "
                    " source_turn_ids_json, relevance_score, access_count, "
                    " consolidated_from_json, is_active, "
                    " created_at_utc, updated_at_utc) "
                    "VALUES (:uid, :sid, :mtype, :content, :summary, "
                    " CAST(:turns AS jsonb), :rel, :acc, "
                    " CAST(:consolidated AS jsonb), true, NOW(), NOW()) "
                    "RETURNING id, created_at_utc, updated_at_utc"
                ),
                {
                    "uid": record.user_id,
                    "sid": record.session_id,
                    "mtype": record.memory_type.value,
                    "content": record.content,
                    "summary": record.summary,
                    "turns": json.dumps(record.source_turn_ids_json),
                    "rel": record.relevance_score,
                    "acc": record.access_count,
                    "consolidated": json.dumps(record.consolidated_from_json),
                },
            )
            row = result.mappings().first()
            if row:
                record.id = row["id"]
                record.created_at_utc = row["created_at_utc"]
                record.updated_at_utc = row["updated_at_utc"]
            await session.commit()
            return record

    async def save_batch(self, records: list[MemoryRecord]) -> list[MemoryRecord]:
        if not records:
            return []

        values_parts: list[str] = []
        params: dict = {}
        for i, r in enumerate(records):
            values_parts.append(
                f"(:uid_{i}, :sid_{i}, :mtype_{i}, :content_{i}, :summary_{i}, "
                f" CAST(:turns_{i} AS jsonb), :rel_{i}, :acc_{i}, "
                f" CAST(:consolidated_{i} AS jsonb), true, NOW(), NOW())"
            )
            params.update({
                f"uid_{i}": r.user_id,
                f"sid_{i}": r.session_id,
                f"mtype_{i}": r.memory_type.value,
                f"content_{i}": r.content,
                f"summary_{i}": r.summary,
                f"turns_{i}": json.dumps(r.source_turn_ids_json),
                f"rel_{i}": r.relevance_score,
                f"acc_{i}": r.access_count,
                f"consolidated_{i}": json.dumps(r.consolidated_from_json),
            })

        values_sql = ",\n".join(values_parts)
        async with self._session_factory() as session:
            result = await session.execute(
                sa_text(
                    f"INSERT INTO memory_records "
                    f"(user_id, session_id, memory_type, content, summary, "
                    f" source_turn_ids_json, relevance_score, access_count, "
                    f" consolidated_from_json, is_active, "
                    f" created_at_utc, updated_at_utc) "
                    f"VALUES {values_sql} "
                    f"RETURNING id, created_at_utc, updated_at_utc "
                    f"ORDER BY created_at_utc"
                ),
                params,
            )
            rows = result.mappings().all()
            for rec, row in zip(records, rows):
                rec.id = row["id"]
                rec.created_at_utc = row["created_at_utc"]
                rec.updated_at_utc = row["updated_at_utc"]
            await session.commit()
            return records

    async def get(self, memory_id: int) -> MemoryRecord | None:
        async with self._session_factory() as session:
            result = await session.execute(
                sa_text(
                    "SELECT id, user_id, session_id, memory_type, content, summary, "
                    " source_turn_ids_json, relevance_score, access_count, "
                    " last_accessed_at_utc, consolidated_from_json, is_active, "
                    " expires_at_utc, created_at_utc, updated_at_utc "
                    "FROM memory_records WHERE id = :mid AND is_active = true"
                ),
                {"mid": memory_id},
            )
            row = result.mappings().first()
            return self._row_to_record(row) if row else None

    async def search(self, query: MemoryQuery, embedding: list[float]) -> list[MemoryRecord]:
        async with self._session_factory() as session:
            type_filter = ""
            params: dict = {
                "uid": query.user_id,
                "top_k": query.top_k,
                "min_rel": query.min_relevance,
            }
            if query.memory_types:
                types = [t.value for t in query.memory_types]
                type_filter = "AND memory_type = ANY(:types)"
                params["types"] = types

            # pgvector cosine similarity search
            result = await session.execute(
                sa_text(
                    "SELECT r.id, r.user_id, r.session_id, r.memory_type, r.content, r.summary, "
                    " r.source_turn_ids_json, r.relevance_score, r.access_count, "
                    " r.last_accessed_at_utc, r.consolidated_from_json, r.is_active, "
                    " r.expires_at_utc, r.created_at_utc, r.updated_at_utc, "
                    " 1 - (e.vector <=> CAST(:vec AS vector)) as similarity "
                    "FROM memory_records r "
                    "JOIN memory_embeddings e ON e.memory_id = r.id "
                    "WHERE r.user_id = :uid AND r.is_active = true "
                    f"AND 1 - (e.vector <=> CAST(:vec AS vector)) >= :min_rel "
                    f"{type_filter} "
                    "ORDER BY e.vector <=> CAST(:vec AS vector) "
                    "LIMIT :top_k"
                ),
                {**params, "vec": str(embedding)},
            )
            records = []
            for row in result.mappings().all():
                rec = self._row_to_record(row)
                rec.relevance_score = round(float(row.get("similarity", 0)), 4)
                records.append(rec)

            # Batch update access count (single UPDATE instead of N individual ones)
            if records:
                ids = [rec.id for rec in records]
                await session.execute(
                    sa_text(
                        "UPDATE memory_records SET access_count = access_count + 1, "
                        "last_accessed_at_utc = NOW(), updated_at_utc = NOW() "
                        "WHERE id = ANY(:ids)"
                    ),
                    {"ids": ids},
                )
            await session.commit()
            return records

    async def deactivate(self, memory_id: int) -> bool:
        """Deactivate a memory record. Returns True if a row was updated, False if not found."""
        async with self._session_factory() as session:
            result = await session.execute(
                sa_text(
                    "UPDATE memory_records SET is_active = false, updated_at_utc = NOW() "
                    "WHERE id = :mid AND is_active = true "
                    "RETURNING id"
                ),
                {"mid": memory_id},
            )
            updated = result.rowcount and result.rowcount > 0
            await session.commit()
            return updated

    async def delete(self, memory_id: int) -> bool:
        """Hard-delete a memory record and its embedding (cascaded by FK).
        Returns True if a row was deleted, False if not found."""
        async with self._session_factory() as session:
            result = await session.execute(
                sa_text("DELETE FROM memory_records WHERE id = :mid RETURNING id"),
                {"mid": memory_id},
            )
            deleted = result.rowcount and result.rowcount > 0
            await session.commit()
            return deleted

    async def list_by_user(
        self, user_id: str, memory_type: MemoryType | None = None,
        page: int = 1, page_size: int = 20,
    ) -> tuple[list[MemoryRecord], int]:
        conditions = ["user_id = :uid", "is_active = true"]
        params: dict = {"uid": user_id, "lim": page_size, "offset": (page - 1) * page_size}
        if memory_type:
            conditions.append("memory_type = :mtype")
            params["mtype"] = memory_type.value

        where = " WHERE " + " AND ".join(conditions)

        async with self._session_factory() as session:
            count_result = await session.execute(
                sa_text(f"SELECT COUNT(*) FROM memory_records{where}"), params,
            )
            total = int(count_result.scalar_one())

            result = await session.execute(
                sa_text(
                    f"SELECT id, user_id, session_id, memory_type, content, summary, "
                    f" source_turn_ids_json, relevance_score, access_count, "
                    f" last_accessed_at_utc, consolidated_from_json, is_active, "
                    f" expires_at_utc, created_at_utc, updated_at_utc "
                    f"FROM memory_records{where} "
                    f"ORDER BY updated_at_utc DESC LIMIT :lim OFFSET :offset"
                ),
                params,
            )
            records = [self._row_to_record(row) for row in result.mappings().all()]
            return records, total

    async def count_by_type(self, user_id: str) -> dict[str, int]:
        async with self._session_factory() as session:
            result = await session.execute(
                sa_text(
                    "SELECT memory_type, COUNT(*) as cnt "
                    "FROM memory_records WHERE user_id = :uid AND is_active = true "
                    "GROUP BY memory_type"
                ),
                {"uid": user_id},
            )
            return {row["memory_type"]: int(row["cnt"]) for row in result.mappings().all()}

    async def save_embedding(self, memory_id: int, embedding: list[float], model: str = "") -> None:
        async with self._session_factory() as session:
            await session.execute(
                sa_text(
                    "INSERT INTO memory_embeddings (memory_id, embedding_model, vector, created_at_utc, updated_at_utc) "
                    "VALUES (:mid, :model, CAST(:vec AS vector), NOW(), NOW()) "
                    "ON CONFLICT (memory_id) DO UPDATE SET vector = CAST(:vec AS vector), updated_at_utc = NOW()"
                ),
                {"mid": memory_id, "model": model, "vec": str(embedding)},
            )
            await session.commit()

    @staticmethod
    def _row_to_record(row) -> MemoryRecord:
        turns_raw = row.get("source_turn_ids_json", "[]")
        cons_raw = row.get("consolidated_from_json", "[]")
        return MemoryRecord(
            id=row["id"],
            user_id=row["user_id"],
            session_id=row.get("session_id"),
            memory_type=MemoryType(row["memory_type"]),
            content=row["content"],
            summary=row.get("summary"),
            source_turn_ids_json=json.loads(turns_raw) if isinstance(turns_raw, str) else (turns_raw or []),
            relevance_score=float(row.get("relevance_score", 0)),
            access_count=int(row.get("access_count", 0)),
            last_accessed_at_utc=row.get("last_accessed_at_utc"),
            consolidated_from_json=json.loads(cons_raw) if isinstance(cons_raw, str) else (cons_raw or []),
            is_active=row.get("is_active", True),
            expires_at_utc=row.get("expires_at_utc"),
            created_at_utc=row.get("created_at_utc"),
            updated_at_utc=row.get("updated_at_utc"),
        )
