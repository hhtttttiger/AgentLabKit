"""聊天历史持久化 — SQLite 存储。"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path.home() / ".config" / "agentlabkit" / "chat.db"


@dataclass
class ChatMessage:
    id: int = 0
    role: str = ""        # "user" | "assistant" | "system"
    content: str = ""
    timestamp: str = ""


class ChatStore:
    """SQLite 聊天记录存储。"""

    def __init__(self, db_path: Path = DB_PATH):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        self._conn.commit()

    def add(self, role: str, content: str) -> ChatMessage:
        now = datetime.now(timezone.utc).isoformat()
        cur = self._conn.execute(
            "INSERT INTO messages (role, content, timestamp) VALUES (?, ?, ?)",
            (role, content, now),
        )
        self._conn.commit()
        return ChatMessage(id=cur.lastrowid, role=role, content=content, timestamp=now)

    def recent(self, limit: int = 50) -> list[ChatMessage]:
        rows = self._conn.execute(
            "SELECT id, role, content, timestamp FROM messages ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            ChatMessage(id=r["id"], role=r["role"], content=r["content"], timestamp=r["timestamp"])
            for r in reversed(rows)
        ]

    def clear(self):
        self._conn.execute("DELETE FROM messages")
        self._conn.commit()

    def close(self):
        self._conn.close()
