"""PostgreSQL smoke test for the destructive migration baseline.

Run explicitly against a disposable PostgreSQL database with:
RUN_MIGRATION_INTEGRATION=1 APP_DB_HOST=... APP_DB_USER=... \
APP_DB_PASSWORD=... APP_DB_NAME=... pytest tests/test_migration_baseline.py
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.environ.get("RUN_MIGRATION_INTEGRATION") != "1",
    reason="requires an explicitly disposable PostgreSQL database",
)
async def test_fresh_database_matches_current_baseline() -> None:
    backend = Path(__file__).parents[1]
    url = os.environ.get("MIGRATION_TEST_DATABASE_URL")
    if url is None:
        from config import Settings

        url = Settings().database_url

    engine = create_async_engine(url)
    async with engine.begin() as connection:
        await connection.execute(text("DROP SCHEMA public CASCADE"))
        await connection.execute(text("CREATE SCHEMA public"))

    env = os.environ.copy()
    project_root = backend.parent
    package_paths = [backend / "src", *sorted((project_root / "packages").glob("*/src"))]
    env["PYTHONPATH"] = os.pathsep.join(str(path) for path in package_paths)
    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=backend,
        env=env,
        check=True,
    )

    async with engine.begin() as connection:
        assert await connection.scalar(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")) == "vector"
        assert await connection.scalar(text("SELECT extname FROM pg_extension WHERE extname = 'pg_trgm'")) == "pg_trgm"
        assert await connection.scalar(text("SELECT atttypmod FROM pg_attribute WHERE attrelid = 'segment_embeddings'::regclass AND attname = 'vector'")) == 1024
        assert await connection.scalar(text("SELECT 1 FROM pg_indexes WHERE indexname = 'ix_document_segment_content_trgm'")) == 1
        for table in (
            "trace_records",
            "trace_spans",
            "run_records",
            "run_projection_events",
            "eval_run_results",
        ):
            assert await connection.scalar(text("SELECT to_regclass(:table)"), {"table": table}) == table

        vector = "[" + ",".join(["0"] * 1024) + "]"
        smoke_sql = """
            INSERT INTO knowledge_bases (id, name, index_names_json, config_json, status)
            VALUES (900000001, 'baseline', '[]', '{}', 'active');
            INSERT INTO knowledge_documents
                (id, knowledge_base_id, title, source_type, file_size, extra_json, status, segment_count)
            VALUES (900000002, 900000001, 'baseline', 'file', 0, '{}', 'pending', 1);
            INSERT INTO document_segments (id, document_id, segment_index, content, extra_json)
            VALUES (900000003, 900000002, 0, 'baseline content', '{}');
            INSERT INTO segment_embeddings
                (id, segment_id, document_id, knowledge_base_id, embedding_model, vector)
            VALUES (900000004, 900000003, 900000002, 900000001, 'baseline', CAST(':vector' AS vector));
            INSERT INTO memory_records
                (id, user_id, memory_type, content, source_turn_ids_json, relevance_score,
                 access_count, consolidated_from_json, is_active)
            VALUES (900000005, 'baseline', 'semantic', 'baseline', '[]', 0, 0, '[]', true);
            INSERT INTO memory_embeddings (id, memory_id, embedding_model, vector)
            VALUES (900000006, 900000005, 'baseline', CAST(':vector' AS vector));
            INSERT INTO trace_records
                (id, trace_id, root_span_id, run_id, status, total_duration_ms,
                 total_input_tokens, total_output_tokens, cache_write_tokens,
                 cache_read_tokens, total_estimated_cost, span_count,
                 dropped_span_count, sample_reason, attributes_json, schema_version,
                 started_at_utc, completed_at_utc)
            VALUES (900000007, 'baseline-trace', 'baseline-span',
                    '00000000-0000-0000-0000-000000000007', 'ok', 1,
                    0, 0, 0, 0, 0, 1, 0, 'normal', '{}', 1, NOW(), NOW());
            INSERT INTO trace_spans
                (id, span_id, trace_id, name, span_kind, status, instrumentation_scope,
                 started_at_utc, completed_at_utc, duration_ms, attributes_json,
                 events_json, links_json)
            VALUES (900000008, 'baseline-span', 'baseline-trace', 'baseline', 'agent',
                    'ok', '', NOW(), NOW(), 1, '{}', '[]', '[]');
            INSERT INTO run_records (run_id, status, metadata_json, projection_version)
            VALUES ('baseline-run', 'completed', '{}', 1);
            INSERT INTO eval_run_results
                (id, run_id, case_id, actual_output, metric_results_json, overall_score, passed, duration_ms)
            VALUES (900000009, 1, 1, 'baseline', '[]', 1, NULL, 1);
        """.replace(":vector", vector)
        for statement in smoke_sql.split(";"):
            if statement.strip():
                await connection.exec_driver_sql(statement)
        assert await connection.scalar(text("SELECT vector_dims(vector) FROM segment_embeddings WHERE id = 900000004")) == 1024
        assert await connection.scalar(text("SELECT vector_dims(vector) FROM memory_embeddings WHERE id = 900000006")) == 1024
        assert await connection.scalar(text("SELECT passed FROM eval_run_results WHERE id = 900000009")) is None
        assert await connection.scalar(text("SELECT count(*) FROM trace_spans WHERE trace_id = 'baseline-trace'")) == 1
        assert await connection.scalar(text("SELECT count(*) FROM run_records WHERE run_id = 'baseline-run'")) == 1

        await connection.execute(text(
            "INSERT INTO glossary_categories (id, name) VALUES (900000010, 'baseline')"
        ))
        await connection.execute(text(
            "INSERT INTO glossary_terms (id, category_id, term) VALUES (900000011, 900000010, 'unique')"
        ))
        with pytest.raises(IntegrityError):
            await connection.execute(text(
                "INSERT INTO glossary_terms (id, category_id, term) VALUES (900000012, 900000010, 'unique')"
            ))

    await engine.dispose()
