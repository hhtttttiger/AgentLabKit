from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from application.execution.run_projection import RunRecord, RunReader, RunWriter
from application.ports.datasets import DatasetExampleWriter, DatasetReader
from application.ports.evaluation import EvaluationRunReader, EvaluationRunStore
from evaluation.contracts_v2 import DatasetExample, EvaluationResult, EvaluationRun, EvaluationRunStatus


def utc_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


class LocalDatabase:
    """Small, explicit SQLite persistence for Desktop Local Mode.

    This is not a general persistence framework.  The schema is intentionally
    local and stores JSON fields as TEXT, UUIDs as TEXT, and timestamps as ISO
    strings.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.connection = sqlite3.connect(str(path), check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def _create_schema(self) -> None:
        with self._lock, self.connection:
            self.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS local_agents (
                    agent_key TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    model TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    kind TEXT NOT NULL DEFAULT 'native',
                    availability TEXT NOT NULL DEFAULT 'ready',
                    executable TEXT,
                    availability_message TEXT
                );
                CREATE TABLE IF NOT EXISTS local_runs (
                    run_id TEXT PRIMARY KEY,
                    trace_id TEXT,
                    user_id TEXT,
                    status TEXT NOT NULL,
                    target_type TEXT,
                    target_key TEXT,
                    target_version TEXT,
                    input_json TEXT,
                    output_json TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    duration_ms INTEGER,
                    session_id TEXT,
                    error_code TEXT,
                    error_message TEXT,
                    metadata_json TEXT NOT NULL,
                    projection_version INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT
                );
                CREATE INDEX IF NOT EXISTS ix_local_runs_started ON local_runs(started_at DESC);
                CREATE TABLE IF NOT EXISTS local_datasets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS local_cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset_id INTEGER NOT NULL REFERENCES local_datasets(id) ON DELETE CASCADE,
                    case_index INTEGER NOT NULL,
                    input_text TEXT NOT NULL,
                    expected_output TEXT,
                    context_json TEXT NOT NULL DEFAULT '[]',
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS ix_local_cases_dataset ON local_cases(dataset_id, case_index);
                CREATE TABLE IF NOT EXISTS local_eval_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    dataset_id INTEGER NOT NULL,
                    target_type TEXT NOT NULL DEFAULT 'agent',
                    target_key TEXT NOT NULL,
                    metric_configs_json TEXT NOT NULL DEFAULT '[]',
                    judge_model_key TEXT NOT NULL DEFAULT '',
                    working_directory TEXT
                );
                CREATE TABLE IF NOT EXISTS local_eval_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_id INTEGER NOT NULL,
                    dataset_id INTEGER NOT NULL,
                    agent_key TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    summary_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS local_eval_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    eval_run_id INTEGER NOT NULL REFERENCES local_eval_runs(id) ON DELETE CASCADE,
                    case_id INTEGER NOT NULL,
                    actual_output TEXT NOT NULL,
                    metric_results_json TEXT NOT NULL DEFAULT '[]',
                    overall_score REAL,
                    passed INTEGER,
                    error_message TEXT,
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    candidate_run_id TEXT,
                    candidate_trace_id TEXT
                );
                CREATE TABLE IF NOT EXISTS local_traces (
                    trace_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    session_id TEXT,
                    status TEXT NOT NULL,
                    attributes_json TEXT NOT NULL DEFAULT '{}',
                    started_at TEXT,
                    completed_at TEXT
                );
                """
            )
            # Local Mode databases from v0.2 predate the agent catalog fields.
            # Keep the migration deliberately explicit and idempotent.
            columns = {row[1] for row in self.connection.execute("PRAGMA table_info(local_agents)").fetchall()}
            for name, definition in (
                ("kind", "TEXT NOT NULL DEFAULT 'native'"),
                ("availability", "TEXT NOT NULL DEFAULT 'ready'"),
                ("executable", "TEXT"),
                ("availability_message", "TEXT"),
            ):
                if name not in columns:
                    self.connection.execute(f"ALTER TABLE local_agents ADD COLUMN {name} {definition}")
            config_columns = {row[1] for row in self.connection.execute("PRAGMA table_info(local_eval_configs)").fetchall()}
            if "working_directory" not in config_columns:
                self.connection.execute("ALTER TABLE local_eval_configs ADD COLUMN working_directory TEXT")
            self.connection.execute(
                "INSERT OR IGNORE INTO local_agents(agent_key, display_name, version, model, kind, availability) VALUES (?, ?, ?, ?, ?, ?)",
                ("local-agent", "Local Agent", "1", "configured", "native", "ready"),
            )

    def close(self) -> None:
        with self._lock:
            self.connection.close()

    def json(self, value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)

    def value(self, value: str | None, default: Any) -> Any:
        if not value:
            return default
        return json.loads(value)


class LocalRunStore(RunReader, RunWriter):
    def __init__(self, db: LocalDatabase) -> None:
        self.db = db

    def _record(self, row: sqlite3.Row) -> RunRecord:
        return RunRecord(
            run_id=row["run_id"], trace_id=row["trace_id"], user_id=row["user_id"],
            status=row["status"], target_type=row["target_type"], target_key=row["target_key"],
            target_version=row["target_version"], input=self.db.value(row["input_json"], None),
            output=self.db.value(row["output_json"], None), started_at=parse_dt(row["started_at"]),
            completed_at=parse_dt(row["completed_at"]), duration_ms=row["duration_ms"],
            session_id=row["session_id"], error_code=row["error_code"], error_message=row["error_message"],
            metadata=self.db.value(row["metadata_json"], {}), updated_at=parse_dt(row["updated_at"]),
            projection_version=row["projection_version"],
        )

    async def get_run(self, run_id: str) -> RunRecord | None:
        row = self.db.connection.execute("SELECT * FROM local_runs WHERE run_id = ?", (run_id,)).fetchone()
        return self._record(row) if row else None

    async def list_runs(self, *, user_id: str, limit: int, offset: int = 0) -> list[RunRecord]:
        rows = self.db.connection.execute(
            "SELECT * FROM local_runs WHERE (? IS NULL OR user_id = ?) ORDER BY started_at DESC LIMIT ? OFFSET ?",
            (user_id, user_id, limit, offset),
        ).fetchall()
        return [self._record(row) for row in rows]

    async def count_runs(self, *, user_id: str) -> int:
        return int(self.db.connection.execute(
            "SELECT COUNT(*) FROM local_runs WHERE (? IS NULL OR user_id = ?)", (user_id, user_id)
        ).fetchone()[0])

    async def project_event(self, event: Any) -> None:
        # The Runtime completion snapshot is authoritative for Local Mode.
        # Lifecycle events are retained through finalize, avoiding a second
        # local projection implementation while preserving Run identity.
        return None

    async def finalize(self, run: Any) -> None:
        target = run.target
        now = utc_iso(run.finished_at or run.started_at)
        with self.db._lock, self.db.connection:
            self.db.connection.execute(
                """INSERT INTO local_runs(
                    run_id, trace_id, user_id, status, target_type, target_key,
                    target_version, input_json, output_json, started_at, completed_at,
                    duration_ms, session_id, error_code, error_message, metadata_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    trace_id=excluded.trace_id, user_id=excluded.user_id, status=excluded.status,
                    target_type=excluded.target_type, target_key=excluded.target_key,
                    target_version=excluded.target_version, input_json=excluded.input_json,
                    output_json=excluded.output_json, started_at=excluded.started_at,
                    completed_at=excluded.completed_at, duration_ms=excluded.duration_ms,
                    session_id=excluded.session_id, error_code=excluded.error_code,
                    error_message=excluded.error_message, metadata_json=excluded.metadata_json,
                    updated_at=excluded.updated_at
                """,
                (
                    run.run_id, run.trace_id, run.user_id, run.status.value,
                    target.type, target.agent_key, target.agent_version,
                    self.db.json(run.input), self.db.json(run.output), utc_iso(run.started_at),
                    utc_iso(run.finished_at), run.duration_ms, run.session_id,
                    run.error.code if run.error else None, run.error.message if run.error else None,
                    self.db.json(run.metadata), now,
                ),
            )
            if run.trace_id:
                self.db.connection.execute(
                    """INSERT INTO local_traces(trace_id, run_id, session_id, status, attributes_json, started_at, completed_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(trace_id) DO UPDATE SET status=excluded.status, completed_at=excluded.completed_at""",
                    (run.trace_id, run.run_id, run.session_id, run.status.value, self.db.json(run.metadata), utc_iso(run.started_at), utc_iso(run.finished_at)),
                )


class LocalAgentReader:
    async def resolve(self, agent_key: str, version: str | None = None) -> Any:
        from agent_runtime.contracts.run import RunTarget
        row = self.db.connection.execute(
            "SELECT agent_key, version, kind FROM local_agents WHERE agent_key = ? AND enabled = 1", (agent_key,)
        ).fetchone()
        if row is None:
            raise LookupError(f"agent {agent_key} not found or not published")
        return RunTarget(type="agent", kind=row["kind"], agent_key=row["agent_key"], agent_version=row["version"])

    def __init__(self, db: LocalDatabase) -> None:
        self.db = db


class LocalDatasetStore(DatasetReader, DatasetExampleWriter):
    def __init__(self, db: LocalDatabase) -> None:
        self.db = db

    def dataset_view(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": str(row["id"]), "name": row["name"], "description": row["description"],
            "tags": self.db.value(row["tags_json"], []), "caseCount": int(row["case_count"] if "case_count" in row.keys() else 0),
            "isActive": bool(row["is_active"]), "createdAtUtc": row["created_at"], "updatedAtUtc": row["updated_at"],
        }

    async def list(self, page: int = 1, page_size: int = 20) -> tuple[list[dict[str, Any]], int]:
        total = int(self.db.connection.execute("SELECT COUNT(*) FROM local_datasets WHERE is_active = 1").fetchone()[0])
        rows = self.db.connection.execute("SELECT d.*, COUNT(c.id) AS case_count FROM local_datasets d LEFT JOIN local_cases c ON c.dataset_id=d.id WHERE d.is_active=1 GROUP BY d.id ORDER BY d.id DESC LIMIT ? OFFSET ?", (page_size, (page - 1) * page_size)).fetchall()
        return [self.dataset_view(row) for row in rows], total

    async def create(self, name: str, description: str | None = None, tags: list[str] | None = None) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self.db._lock, self.db.connection:
            cur = self.db.connection.execute("INSERT INTO local_datasets(name, description, tags_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)", (name, description, self.db.json(tags or []), now, now))
            row = self.db.connection.execute("SELECT d.*, 0 AS case_count FROM local_datasets d WHERE d.id=?", (cur.lastrowid,)).fetchone()
        return self.dataset_view(row)

    async def cases(self, dataset_id: str) -> list[dict[str, Any]]:
        rows = self.db.connection.execute("SELECT * FROM local_cases WHERE dataset_id=? ORDER BY case_index", (int(dataset_id),)).fetchall()
        return [{"id": str(row["id"]), "datasetId": str(row["dataset_id"]), "caseIndex": row["case_index"], "inputText": row["input_text"], "expectedOutput": row["expected_output"], "context": self.db.value(row["context_json"], []), "tags": self.db.value(row["tags_json"], []), "sourceRunId": self.db.value(row["metadata_json"], {}).get("source_run_id")} for row in rows]

    async def case_for_source_run(self, run_id: str) -> dict[str, Any] | None:
        rows = self.db.connection.execute("SELECT * FROM local_cases ORDER BY id").fetchall()
        for row in rows:
            metadata = self.db.value(row["metadata_json"], {})
            if metadata.get("source_run_id") == run_id:
                return {"id": str(row["id"]), "datasetId": str(row["dataset_id"]), "inputText": row["input_text"]}
        return None

    async def get_examples(self, dataset_id: str) -> list[DatasetExample]:
        rows = self.db.connection.execute("SELECT * FROM local_cases WHERE dataset_id=? ORDER BY case_index", (int(dataset_id),)).fetchall()
        return [DatasetExample(example_id=str(row["id"]), dataset_id=str(row["dataset_id"]), input_text=row["input_text"], expected_output=row["expected_output"], context=self.db.value(row["context_json"], []), tags=self.db.value(row["tags_json"], []), metadata=self.db.value(row["metadata_json"], {}), source_run_id=self.db.value(row["metadata_json"], {}).get("source_run_id"), source_trace_id=self.db.value(row["metadata_json"], {}).get("source_trace_id")) for row in rows]

    async def create_example(self, *, dataset_id: str, input_text: Any, expected_output: Any | None, metadata: dict[str, Any], source_run_id: str, source_trace_id: str | None) -> DatasetExample:
        row = self.db.connection.execute("SELECT COALESCE(MAX(case_index), -1) + 1 FROM local_cases WHERE dataset_id=?", (int(dataset_id),)).fetchone()
        merged = dict(metadata)
        merged.update({"source_run_id": source_run_id, "source_trace_id": source_trace_id})
        with self.db._lock, self.db.connection:
            cur = self.db.connection.execute("INSERT INTO local_cases(dataset_id, case_index, input_text, expected_output, metadata_json) VALUES (?, ?, ?, ?, ?)", (int(dataset_id), row[0], str(input_text), expected_output, self.db.json(merged)))
        return DatasetExample(example_id=str(cur.lastrowid), dataset_id=dataset_id, input_text=input_text, expected_output=expected_output, metadata=merged, source_run_id=source_run_id, source_trace_id=source_trace_id)

    async def create_cases(self, dataset_id: str, cases: list[dict[str, Any]]) -> dict[str, int]:
        start = int(self.db.connection.execute("SELECT COALESCE(MAX(case_index), -1) + 1 FROM local_cases WHERE dataset_id=?", (int(dataset_id),)).fetchone()[0])
        with self.db._lock, self.db.connection:
            for index, case in enumerate(cases):
                self.db.connection.execute("INSERT INTO local_cases(dataset_id, case_index, input_text, expected_output, context_json, tags_json) VALUES (?, ?, ?, ?, ?, ?)", (int(dataset_id), start + index, case["inputText"], case.get("expectedOutput"), self.db.json(case.get("context", [])), self.db.json(case.get("tags", []))))
        return {"added": len(cases), "total": start + len(cases)}


class LocalEvaluationStore(EvaluationRunReader, EvaluationRunStore):
    def __init__(self, db: LocalDatabase) -> None:
        self.db = db

    async def start(self, *, dataset_id: str, agent_key: str, total_examples: int) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self.db._lock, self.db.connection:
            cur = self.db.connection.execute("INSERT INTO local_eval_runs(config_id, dataset_id, agent_key, status, started_at) VALUES (0, ?, ?, 'running', ?)", (int(dataset_id), agent_key, now))
        return {"id": cur.lastrowid, "dataset_id": dataset_id, "agent_key": agent_key}

    async def record_result(self, evaluation_run: dict[str, Any], result: EvaluationResult) -> None:
        with self.db._lock, self.db.connection:
            self.db.connection.execute("INSERT INTO local_eval_results(eval_run_id, case_id, actual_output, metric_results_json, overall_score, passed, error_message, duration_ms, candidate_run_id, candidate_trace_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (evaluation_run["id"], int(result.example_id), str(result.details.get("actual_output", "")), self.db.json(result.details.get("metric_results", [])), result.score, None if result.passed is None else int(result.passed), result.message, result.duration_ms, result.run_id, result.details.get("candidate_trace_id")))

    async def complete(self, evaluation_run: dict[str, Any]) -> dict[str, Any]:
        rows = self.db.connection.execute("SELECT overall_score FROM local_eval_results WHERE eval_run_id=?", (evaluation_run["id"],)).fetchall()
        scores = [row[0] for row in rows if row[0] is not None]
        summary = {"total_cases": len(rows), "avg_score": round(sum(scores) / len(scores), 4) if scores else None}
        with self.db._lock, self.db.connection:
            self.db.connection.execute("UPDATE local_eval_runs SET status='completed', completed_at=?, summary_json=? WHERE id=?", (datetime.now(timezone.utc).isoformat(), self.db.json(summary), evaluation_run["id"]))
        return {**evaluation_run, "status": "completed", "summary": summary}

    async def fail(self, evaluation_run: dict[str, Any], error: Exception) -> dict[str, Any]:
        with self.db._lock, self.db.connection:
            self.db.connection.execute("UPDATE local_eval_runs SET status='failed', completed_at=?, summary_json=? WHERE id=?", (datetime.now(timezone.utc).isoformat(), self.db.json({"error": str(error)}), evaluation_run["id"]))
        return {**evaluation_run, "status": "failed"}

    async def get_run(self, run_id: str) -> EvaluationRun | None:
        row = self.db.connection.execute("SELECT * FROM local_eval_runs WHERE id=?", (int(run_id),)).fetchone()
        if not row:
            return None
        summary = self.db.value(row["summary_json"], {})
        return EvaluationRun(run_id=str(row["id"]), dataset_id=str(row["dataset_id"]), agent_key=row["agent_key"], status=EvaluationRunStatus(row["status"]), total_examples=summary.get("total_cases", 0), completed_examples=summary.get("total_cases", 0), overall_score=summary.get("avg_score"))

    async def list_results(self, run_id: str) -> list[EvaluationResult]:
        rows = self.db.connection.execute("SELECT * FROM local_eval_results WHERE eval_run_id=? ORDER BY id", (int(run_id),)).fetchall()
        return [EvaluationResult(evaluator_name="local.output_match", example_id=str(row["case_id"]), score=row["overall_score"], passed=None if row["passed"] is None else bool(row["passed"]), message=row["error_message"], details={"actual_output": row["actual_output"], "metric_results": self.db.value(row["metric_results_json"], [])}, duration_ms=row["duration_ms"], run_id=row["candidate_run_id"]) for row in rows]
