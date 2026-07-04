"""Register agent_runtime's bundled built-in tools into the runtime registry.

``agent_runtime`` ships ready-made built-ins (``time_now``, ``calculator``), but
``ToolRegistry.__post_init__`` only auto-registers ``knowledge_search``. The
others exist as dead code until someone calls ``register()`` on them — without
this step, any agent that binds ``time_now`` is silently dropped by
``ToolFilter`` (binding references an unregistered tool → WARNING + skip).

Kept in a standalone, import-safe module so the lifespan wiring in
:mod:`main` stays thin and the registration is unit-testable without a DB.
Importing ``agent_runtime.tools.builtin`` pulls only runtime-internal code —
no retrieval chain — so it is safe to call unconditionally at startup.
"""

from __future__ import annotations

from agent_runtime.tools.builtin import CalculatorTool, TimeNowTool
from agent_runtime.tools.registry import ToolRegistry


def register_builtin_tools(registry: ToolRegistry) -> None:
    """Register the bundled utility built-ins that ``ToolRegistry`` does not.

    ``knowledge_search`` is already auto-registered in
    ``ToolRegistry.__post_init__``; here we add the two remaining built-ins so
    agents can bind them. ``register`` raises ``ValueError`` on duplicates, but
    these names never collide with ``knowledge_search`` and every process gets
    a fresh registry, so re-running on restart is safe.
    """
    registry.register(TimeNowTool.spec, TimeNowTool())  # name="time_now"
    registry.register(CalculatorTool.spec, CalculatorTool())  # name="calculator"
