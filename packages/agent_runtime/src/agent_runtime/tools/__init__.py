"""Dynamic tool system for agent_runtime.

Core abstractions
-----------------
:class:`DynamicToolRegistry`  — register, filter, and build tools at runtime.
:class:`ToolRegistry`          — backward-compat wrapper; same API as before.
:class:`ToolExecutor`          — isolated execution: timeout + retry + schema.
:class:`ToolFilter`            — reconcile registered tools with agent bindings.
:class:`SchemaValidator`       — validate argument dicts against JSON Schema.

Contracts (data classes)
------------------------
:class:`ToolSpec`              — immutable tool metadata.
:class:`ToolBinding`           — per-agent binding from the definition layer.
:class:`ToolHandler`           — protocol every tool implementation must satisfy.
:class:`ToolResult`            — structured execution outcome.
:class:`ToolExecutionContext`  — runtime context injected into tool handlers.

Built-in tools
--------------
:class:`~builtin.KnowledgeSearchTool`
:class:`~builtin.TimeNowTool`
:class:`~builtin.CalculatorTool`
"""

from .builtin import CalculatorTool, KnowledgeSearchTool, TimeNowTool
from .catalog_syncer import DbBackedExternalToolLoader, ToolCatalogSyncer
from .contracts import (
    ToolBinding,
    ToolExecutionContext,
    ToolExecutionMode,
    ToolHandler,
    ToolResult,
    ToolSpec,
    binding_from_snapshot,
)
from .executor import ToolExecutor
from .external import ExternalToolConfig, HttpToolHandler
from .filter import ToolFilter
from .registry import (
    ConservativeHandoffPolicy,
    DynamicToolRegistry,
    HandoffPolicy,
    KnowledgeProvider,
    NullKnowledgeProvider,
    ToolRegistry,
)
from .schema_validator import SchemaValidator, validate_arguments

__all__ = [
    # Registry
    "DynamicToolRegistry",
    "ToolRegistry",
    # Executor & Validator
    "ToolExecutor",
    "ToolFilter",
    "SchemaValidator",
    "validate_arguments",
    # Contracts
    "ToolSpec",
    "ToolBinding",
    "ToolExecutionMode",
    "ToolHandler",
    "ToolResult",
    "ToolExecutionContext",
    "binding_from_snapshot",
    # External tool framework
    "ExternalToolConfig",
    "HttpToolHandler",
    # Catalog sync
    "ToolCatalogSyncer",
    "DbBackedExternalToolLoader",
    # Legacy protocols & defaults
    "ConservativeHandoffPolicy",
    "HandoffPolicy",
    "KnowledgeProvider",
    "NullKnowledgeProvider",
    # Built-in tools
    "CalculatorTool",
    "KnowledgeSearchTool",
    "TimeNowTool",
]
