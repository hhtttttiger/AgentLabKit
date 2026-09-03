import ast
from pathlib import Path


FORBIDDEN_ROOTS = {"backend", "fastapi", "starlette"}


def _imports(root: Path) -> set[str]:
    names: set[str] = set()
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module.split(".", 1)[0])
    return names


def test_application_has_no_framework_or_backend_imports():
    root = Path(__file__).parents[1] / "src" / "application"
    assert not (_imports(root) & FORBIDDEN_ROOTS)


def test_domain_packages_do_not_import_application():
    repo = Path(__file__).parents[3]
    for package in ("agent_runtime", "evaluation", "observability", "cost_analysis"):
        root = repo / "packages" / package / "src"
        assert root.exists()
        assert "application" not in _imports(root), package
