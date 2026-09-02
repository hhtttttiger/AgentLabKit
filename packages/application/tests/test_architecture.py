from pathlib import Path


def test_application_has_no_framework_or_backend_imports():
    root = Path(__file__).parents[1] / "src" / "application"
    source = "\n".join(p.read_text() for p in root.rglob("*.py"))
    assert "import fastapi" not in source
    assert "import starlette" not in source
    assert "import backend" not in source
