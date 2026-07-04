"""Built-in tool implementations bundled with agent_runtime.

Each submodule exposes a single class whose name ends in ``Tool``.  Every
tool class must:

1. Declare a class-level :attr:`spec` of type :class:`~agent_runtime.tools.contracts.ToolSpec`.
2. Implement ``async execute(arguments, context) -> ToolResult``.
3. Be self-contained — no side-effect imports at module level.

Public re-exports for convenience:
"""

from .calculator import CalculatorTool
from .knowledge_search import KnowledgeSearchTool
from .time_now import TimeNowTool

__all__ = [
    "CalculatorTool",
    "KnowledgeSearchTool",
    "TimeNowTool",
]
