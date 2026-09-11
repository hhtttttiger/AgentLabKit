"""Import-direction guardrails for the logical Agent Core boundary."""

from __future__ import annotations

import ast
from pathlib import Path


PACKAGE_ROOT = Path(__file__).parents[1]
CORE_MODULES = (
    PACKAGE_ROOT / "src/agent_runtime/runtime/loop.py",
    PACKAGE_ROOT / "src/agent_runtime/runtime/llm_adapter.py",
    PACKAGE_ROOT / "src/agent_runtime/runtime/cancel.py",
    PACKAGE_ROOT / "src/agent_runtime/state.py",
    PACKAGE_ROOT / "src/agent_runtime/contracts/models.py",
)

FORBIDDEN_EXTERNAL_ROOTS = {
    "application",
    "backend",
    "cost_analysis",
    "evaluation",
    "frontend",
    "observability",
    "retrieval",
    "sqlalchemy",
    "agentlabkit_db",
}

FORBIDDEN_RUNTIME_MODULES = {
    "agent_runtime.workflow",
    "agent_runtime.mcp",
    "agent_runtime.definition",
    "agent_runtime.channels.voice",
    "agent_runtime.guardrails",
    "agent_runtime.memory",
    "agent_runtime.orchestration",
    "agent_runtime.skills",
}


def _import_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names.append("." * node.level + module)
    return names


def _external_root(name: str) -> str:
    return name.split(".", 1)[0].lstrip(".")


def test_core_modules_have_no_platform_imports() -> None:
    violations = {
        f"{path.relative_to(PACKAGE_ROOT)} imports {name}"
        for path in CORE_MODULES
        for name in _import_names(path)
        if _external_root(name) in FORBIDDEN_EXTERNAL_ROOTS
    }
    assert not violations, "Agent Core must depend on protocols, not platform implementations:\n" + "\n".join(sorted(violations))


def test_core_modules_do_not_depend_on_runtime_capabilities() -> None:
    violations = {
        f"{path.relative_to(PACKAGE_ROOT)} imports {name}"
        for path in CORE_MODULES
        for name in _import_names(path)
        if name in FORBIDDEN_RUNTIME_MODULES
        or any(name.startswith(module + ".") for module in FORBIDDEN_RUNTIME_MODULES)
    }
    assert not violations, "Agent Core must not import concrete Runtime capabilities:\n" + "\n".join(sorted(violations))


def test_loop_uses_tool_protocol_boundary() -> None:
    names = _import_names(PACKAGE_ROOT / "src/agent_runtime/runtime/loop.py")
    assert any(name.endswith("tools.contracts") for name in names)
    assert not any("mcp" in name or "workflow" in name for name in names)


def test_agent_runtime_has_no_platform_back_edges() -> None:
    violations = {
        f"{path.relative_to(PACKAGE_ROOT)} imports {name}"
        for path in (PACKAGE_ROOT / "src/agent_runtime").rglob("*.py")
        for name in _import_names(path)
        if _external_root(name) in {"application", "backend", "frontend"}
    }
    assert not violations, "agent_runtime must remain independent of transport/application layers:\n" + "\n".join(sorted(violations))


def test_architecture_note_documents_protected_seams() -> None:
    note = (PACKAGE_ROOT / "../../docs/architecture/agent-core-independence.md").resolve()
    text = note.read_text(encoding="utf-8")
    for phrase in ("Runtime owns execution facts", "protected seam", "Workflow is not Agent Core"):
        assert phrase in text
