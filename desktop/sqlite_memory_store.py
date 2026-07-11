"""SqliteMemoryStore — MemoryStore 协议的 SQLite 实现。

向量搜索使用纯 Python 余弦相似度（无 numpy 依赖）。
"""
from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from memory.contracts import MemoryRecord, MemoryType, MemoryQuery
from memory.store import MemoryStore

DB_PATH = Path.home() / ".config" / "agentlabkit" / "memory.db"


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """纯 Python 余弦相似度。"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SqliteMemoryStore:
    """SQLite 实现的 MemoryStore，支持基本 CRUD + 向量搜索。"""

    def __init__(self, db_path: Path = DB_PATH):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS memory_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                session_id TEXT,
                memory_type TEXT NOT NULL DEFAULT 'episodic',
                content TEXT NOT NULL,
                summary TEXT,
                source_turn_ids_json TEXT DEFAULT '[]',
                relevance_score REAL DEFAULT 0.0,
                access_count INTEGER DEFAULT 0,
                last_accessed_at_utc TEXT,
                consolidated_from_json TEXT DEFAULT '[]',
                is_active INTEGER DEFAULT 1,
                expires_at_utc TEXT,
                created_at_utc TEXT NOT NULL,
                updated_at_utc TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_memory_user ON memory_records(user_id, is_active);

            CREATE TABLE IF NOT EXISTS memory_embeddings (
                memory_id INTEGER PRIMARY KEY REFERENCES memory_records(id) ON DELETE CASCADE,
                embedding_model TEXT DEFAULT '',
                vector_json TEXT NOT NULL,
                created_at_utc TEXT NOT NULL,
                updated_at_utc TEXT NOT NULL
            );
        """)
        self._conn.commit()

    def _row_to_record(self, row) -> MemoryRecord:
        return MemoryRecord(
            id=row["id"],
            user_id=row["user_id"],
            session_id=row["session_id"],
            memory_type=MemoryType(row["memory_type"]),
            content=row["content"],
            summary=row["summary"],
            source_turn_ids_json=json.loads(row["source_turn_ids_json"] or "[]"),
            relevance_score=float(row["relevance_score"] or 0),
            access_count=int(row["access_count"] or 0),
            last_accessed_at_utc=row["last_accessed_at_utc"],
            consolidated_from_json=json.loads(row["consolidated_from_json"] or "[]"),
            is_active=bool(row["is_active"]),
            expires_at_utc=row["expires_at_utc"],
            created_at_utc=row["created_at_utc"],
            updated_at_utc=row["updated_at_utc"],
        )

    # ── CRUD ──

    async def save(self, record: MemoryRecord) -> MemoryRecord:
        now = _now()
        cur = self._conn.execute(
            "INSERT INTO memory_records "
            "(user_id, session_id, memory_type, content, summary, "
            " source_turn_ids_json, relevance_score, access_count, "
            " consolidated_from_json, is_active, created_at_utc, updated_at_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
            (
                record.user_id, record.session_id, record.memory_type.value,
                record.content, record.summary,
                json.dumps(record.source_turn_ids_json), record.relevance_score,
                record.access_count, json.dumps(record.consolidated_from_json),
                now, now,
            ),
        )
        self._conn.commit()
        record.id = cur.lastrowid
        record.created_at_utc = now
        record.updated_at_utc = now
        return record

    async def save_batch(self, records: list[MemoryRecord]) -> list[MemoryRecord]:
        for r in records:
            await self.save(r)
        return records

    async def get(self, memory_id: int) -> MemoryRecord | None:
        row = self._conn.execute(
            "SELECT * FROM memory_records WHERE id = ? AND is_active = 1",
            (memory_id,),
        ).fetchone()
        return self._row_to_record(row) if row else None

    async def deactivate(self, memory_id: int) -> bool:
        cur = self._conn.execute(
            "UPDATE memory_records SET is_active = 0, updated_at_utc = ? "
            "WHERE id = ? AND is_active = 1",
            (_now(), memory_id),
        )
        self._conn.commit()
        return cur.rowcount > 0

    async def delete(self, memory_id: int) -> bool:
        cur = self._conn.execute(
            "DELETE FROM memory_records WHERE id = ?", (memory_id,)
        )
        self._conn.commit()
        return cur.rowcount > 0

    async def list_by_user(
        self, user_id: str, memory_type: MemoryType | None = None,
        page: int = 1, page_size: int = 20,
    ) -> tuple[list[MemoryRecord], int]:
        conditions = ["user_id = ?", "is_active = 1"]
        params: list = [user_id]
        if memory_type:
            conditions.append("memory_type = ?")
            params.append(memory_type.value)

        where = " WHERE " + " AND ".join(conditions)

        count_row = self._conn.execute(
            f"SELECT COUNT(*) FROM memory_records{where}", params
        ).fetchone()
        total = count_row[0]

        rows = self._conn.execute(
            f"SELECT * FROM memory_records{where} "
            f"ORDER BY updated_at_utc DESC LIMIT ? OFFSET ?",
            params + [page_size, (page - 1) * page_size],
        ).fetchall()
        return [self._row_to_record(r) for r in rows], total

    async def count_by_type(self, user_id: str) -> dict[str, int]:
        rows = self._conn.execute(
            "SELECT memory_type, COUNT(*) as cnt FROM memory_records "
            "WHERE user_id = ? AND is_active = 1 GROUP BY memory_type",
            (user_id,),
        ).fetchall()
        return {r["memory_type"]: r["cnt"] for r in rows}

    # ── 向量搜索 ──

    async def save_embedding(
        self, memory_id: int, embedding: list[float], model: str = ""
    ) -> None:
        now = _now()
        self._conn.execute(
            "INSERT INTO memory_embeddings (memory_id, embedding_model, vector_json, created_at_utc, updated_at_utc) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(memory_id) DO UPDATE SET vector_json = ?, updated_at_utc = ?",
            (memory_id, model, json.dumps(embedding), now, now, json.dumps(embedding), now),
        )
        self._conn.commit()

    async def search(
        self, query: MemoryQuery, embedding: list[float]
    ) -> list[MemoryRecord]:
        # 获取该用户的所有活跃记忆 + 嵌入向量
        sql = (
            "SELECT r.*, e.vector_json "
            "FROM memory_records r "
            "JOIN memory_embeddings e ON e.memory_id = r.id "
            "WHERE r.user_id = ? AND r.is_active = 1"
        )
        params: list = [query.user_id]

        if query.memory_types:
            placeholders = ",".join("?" for _ in query.memory_types)
            sql += f" AND r.memory_type IN ({placeholders})"
            params.extend(t.value for t in query.memory_types)

        rows = self._conn.execute(sql, params).fetchall()

        # 计算余弦相似度，过滤 + 排序
        scored = []
        for row in rows:
            vec = json.loads(row["vector_json"])
            sim = _cosine_similarity(embedding, vec)
            if sim >= query.min_relevance:
                scored.append((sim, row))

        scored.sort(key=lambda x: x[0], reverse=True)
        scored = scored[: query.top_k]

        # 更新访问计数
        if scored:
            ids = [row["id"] for _, row in scored]
            placeholders = ",".join("?" for _ in ids)
            self._conn.execute(
                f"UPDATE memory_records SET access_count = access_count + 1, "
                f"last_accessed_at_utc = ?, updated_at_utc = ? "
                f"WHERE id IN ({placeholders})",
                [_now(), _now()] + ids,
            )
            self._conn.commit()

        records = []
        for sim, row in scored:
            rec = self._row_to_record(row)
            rec.relevance_score = round(sim, 4)
            records.append(rec)

        return records

    def close(self):
        self._conn.close()
