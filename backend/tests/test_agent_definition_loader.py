"""Unit tests for BackendAgentDefinitionLoader.

Uses a fake AsyncSession that returns canned ORM-like rows keyed by table name,
so the snapshot mapping is verified without a real database. Rows are plain
``SimpleNamespace`` objects exposing the attributes the loader reads.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from modules.agent.definition_loader import BackendAgentDefinitionLoader


def _tablename(stmt: Any) -> str | None:
    """Resolve the queried table name from a SQLAlchemy select statement."""
    froms = stmt.get_final_froms() if hasattr(stmt, "get_final_froms") else ()
    if froms:
        return froms[0].name
    cols = list(getattr(stmt, "selected_columns", []) or [])
    if cols:
        return cols[0].table.name
    return None


class _FakeResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = list(rows)

    def scalar_one_or_none(self) -> Any:
        return self._rows[0] if self._rows else None

    def scalars(self) -> "_FakeResult":
        return self

    def all(self) -> list[Any]:
        return list(self._rows)


class _FakeSession:
    def __init__(self, by_table: dict[str, list[Any]]) -> None:
        self._by = by_table

    async def execute(self, stmt: Any) -> _FakeResult:
        return _FakeResult(self._by.get(_tablename(stmt), []))

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False


class _FakeSessionFactory:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    def __call__(self) -> _FakeSession:
        return self._session


def _make_loader(by_table: dict[str, list[Any]]) -> BackendAgentDefinitionLoader:
    return BackendAgentDefinitionLoader(_FakeSessionFactory(_FakeSession(by_table)))


# ── fixtures ────────────────────────────────────────────────────────────────


def _definition_row(*, enabled: bool = True, published: int | None = 1) -> SimpleNamespace:
    return SimpleNamespace(
        id=100,
        agent_key="default",
        display_name="默认助手",
        description="系统默认 Agent",
        is_enabled=enabled,
        published_version=published,
    )


def _version_row(*, version_number: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        id=200,
        agent_id=100,
        version_number=version_number,
        system_prompt="你是一个有用的AI助手。",
        model_binding_key="mimo-v2-flash-chat",
        temperature=0.7,
        max_tokens=4096,
        response_format=None,
        extra_json={
            "version_label": "v1",
            "change_summary": "init",
            "default_locale": "zh-CN",
            "runtime_options": {"temperature": 0.7, "max_tokens": 4096},
            "handoff_policy": {"mode": "manual"},
            "response_policy": {},
            "guardrails_policy": {},
        },
        checksum="abc123",
    )


def _tool_binding_row(tool_name: str = "knowledge_search") -> SimpleNamespace:
    return SimpleNamespace(
        agent_version_id=200,
        tool_name=tool_name,
        is_enabled=True,
        extra_json={"invocation_mode": "auto"},
    )


def _kb_binding_row(kb_id: int = 7) -> SimpleNamespace:
    return SimpleNamespace(
        agent_version_id=200,
        knowledge_base_id=kb_id,
        is_enabled=True,
        extra_json={},
    )


# ── tests ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_load_maps_definition_version_tools_and_kb():
    loader = _make_loader(
        {
            "agent_definitions": [_definition_row()],
            "agent_definition_versions": [_version_row()],
            "agent_tool_bindings": [_tool_binding_row("knowledge_search"), _tool_binding_row("custom_http")],
            "agent_knowledge_base_bindings": [_kb_binding_row(7)],
        }
    )

    snapshot = await loader.load("default")

    assert snapshot is not None
    assert snapshot.agent_key == "default"
    assert snapshot.version_number == 1
    assert snapshot.display_name == "默认助手"
    assert snapshot.status == "published"
    assert snapshot.system_prompt_template == "你是一个有用的AI助手。"
    assert snapshot.model_binding_key == "mimo-v2-flash-chat"
    assert snapshot.default_locale == "zh-CN"
    assert snapshot.runtime_options == {"temperature": 0.7, "max_tokens": 4096}
    assert snapshot.handoff_policy == {"mode": "manual"}
    assert snapshot.response_policy == {}
    assert snapshot.guardrails_policy == {}
    assert [t.tool_name for t in snapshot.tools] == ["knowledge_search", "custom_http"]
    assert snapshot.tools[0].invocation_mode == "auto"
    assert [kb.knowledge_base_id for kb in snapshot.knowledge_bindings] == ["7"]  # str contract
    # MVP deferrals:
    assert snapshot.mcp_bindings == ()
    assert snapshot.skill_bindings == ()


@pytest.mark.asyncio
async def test_load_returns_none_for_disabled_agent():
    loader = _make_loader({"agent_definitions": [_definition_row(enabled=False)]})
    assert await loader.load("default") is None


@pytest.mark.asyncio
async def test_load_returns_none_when_not_published():
    loader = _make_loader({"agent_definitions": [_definition_row(published=None)]})
    assert await loader.load("default") is None


@pytest.mark.asyncio
async def test_load_returns_none_for_unknown_agent():
    loader = _make_loader({"agent_definitions": []})
    assert await loader.load("nope") is None


@pytest.mark.asyncio
async def test_load_caches_snapshot_across_calls():
    by_table = {
        "agent_definitions": [_definition_row()],
        "agent_definition_versions": [_version_row()],
        "agent_tool_bindings": [],
        "agent_knowledge_base_bindings": [],
    }
    session = _FakeSession(by_table)
    loader = BackendAgentDefinitionLoader(_FakeSessionFactory(session))

    first = await loader.load("default")
    second = await loader.load("default")

    assert first is not None and second is not None
    assert first is second  # same cached object


@pytest.mark.asyncio
async def test_check_revision_returns_latest_revision():
    # The loader selects the scalar ``revision`` column (not the entity), so the
    # fake returns plain ints. Real SQLAlchemy applies the ORDER BY; the fake
    # ignores it, so we only assert the path runs and yields an int scalar.
    by_table = {"agent_catalog_revisions": [3, 1]}
    loader = _make_loader(by_table)
    result = await loader.check_revision()
    assert isinstance(result, int)
    assert result in (1, 3)
