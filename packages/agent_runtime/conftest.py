"""Pytest configuration for agent_runtime tests."""

import sys
import os
import importlib.util

_ROOT = os.path.dirname(__file__)
_SRC = os.path.join(_ROOT, "src")

if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

module = sys.modules.get("agent_runtime")
if module is not None and getattr(module, "__file__", None) is None:
    source_path = os.path.join(_SRC, "agent_runtime")
    package_path = getattr(module, "__path__", None)
    if package_path is not None and source_path not in package_path:
        module.__path__ = [source_path, *list(package_path)]
    spec = importlib.util.spec_from_file_location(
        "agent_runtime",
        os.path.join(source_path, "__init__.py"),
        submodule_search_locations=[source_path],
    )
    if spec is not None and spec.loader is not None:
        module.__file__ = spec.origin
        module.__spec__ = spec
        module.__path__ = [source_path]
        spec.loader.exec_module(module)

collect_ignore = [
    "tests/manual_mcp_test.py",
    "tests/real_mcp_server_test.py",
]
