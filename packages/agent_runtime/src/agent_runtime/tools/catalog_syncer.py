"""Tool catalog helpers for the shared ``agent_tool_definitions`` table.

Responsibilities
----------------
* Load ``http_external`` tool definitions from the DB and register them with
  the :class:`~agent_runtime.tools.registry.DynamicToolRegistry`.

Design choices
--------------
* Uses SQLAlchemy async sessions via the same factory as
  :class:`~agent_runtime.definition.loader.SqlAlchemyAgentDefinitionLoader`.
* ``http_external`` tools are loaded fresh on each startup; credential
  resolution uses environment variables (matching :class:`~agent_runtime.tools.external.HttpToolHandler`).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .contracts import ToolSpec
from .external import ExternalToolConfig, HttpToolHandler

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ORM helpers (lightweight; avoid importing the full definition loader)
# ---------------------------------------------------------------------------

_UPSERT_BUILTIN_SQL = text("""
    INSERT INTO agent_tool_definitions (
        "Id", "ToolName", "DisplayName", "Description",
        "SourceType", "ParametersSchemaJson", "TagsJson",
        "HttpMethod", "TimeoutSeconds", "MaxRetries", "Status",
        "CreatedAtUtc"
    ) VALUES (
        gen_random_uuid(), :tool_name, :display_name, :description,
        'builtin', :params_json, :tags_json,
        'POST', :timeout_seconds, :max_retries, 'active',
        now() AT TIME ZONE 'UTC'
    )
    ON CONFLICT ("ToolName") DO UPDATE SET
        "DisplayName"          = EXCLUDED."DisplayName",
        "Description"          = EXCLUDED."Description",
        "ParametersSchemaJson" = EXCLUDED."ParametersSchemaJson",
        "TagsJson"             = EXCLUDED."TagsJson",
        "TimeoutSeconds"       = EXCLUDED."TimeoutSeconds",
        "MaxRetries"           = EXCLUDED."MaxRetries",
        "UpdatedAtUtc"         = now() AT TIME ZONE 'UTC'
    -- Do NOT touch Status; respect operator-set deprecated/disabled state.
""")

_SELECT_HTTP_EXTERNAL_SQL = text("""
    SELECT "ToolName", "DisplayName", "Description",
           "ParametersSchemaJson", "TagsJson",
           "EndpointUrl", "HttpMethod", "CredentialKey",
           "TimeoutSeconds", "MaxRetries"
    FROM   agent_tool_definitions
    WHERE  "SourceType" = 'http_external'
    AND    "Status"     = 'active'
""")


@dataclass(frozen=True)
class _ExternalToolRow:
    tool_name: str
    display_name: str
    description: str
    parameters_schema: dict[str, Any]
    tags: list[str]
    endpoint_url: str
    http_method: str
    credential_key: str | None
    timeout_seconds: float
    max_retries: int


# ---------------------------------------------------------------------------
# ToolCatalogSyncer
# ---------------------------------------------------------------------------


class ToolCatalogSyncer:
    """Provides lightweight DB access for the shared tool catalog.

    Parameters
    ----------
    session_factory:
        SQLAlchemy async session factory pointed at the shared database.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def upsert_all(self, specs: list[ToolSpec]) -> int:
        """Upsert all ``builtin`` tool specs into the catalog table.

        This helper exists for offline tooling/tests. The normal production path
        keeps DB writes in the .NET management plane.
        """
        if not specs:
            return 0

        try:
            async with self._session_factory() as session:
                async with session.begin():
                    for spec in specs:
                        await session.execute(
                            _UPSERT_BUILTIN_SQL,
                            {
                                "tool_name": spec.name,
                                "display_name": spec.name.replace("_", " ").title(),
                                "description": spec.description,
                                "params_json": json.dumps(spec.parameters_schema),
                                "tags_json": json.dumps(sorted(spec.tags)),
                                "timeout_seconds": spec.timeout_seconds,
                                "max_retries": spec.max_retries,
                            },
                        )
            logger.info("tool_catalog_sync synced=%d", len(specs))
        except Exception as exc:
            # Sync failure must not block service startup
            logger.warning("tool_catalog_sync_failed error=%s", exc)

        return len(specs)

    async def load_external_tools(self) -> list[_ExternalToolRow]:
        """Load all active ``http_external`` tool definitions from the DB.

        Returns an empty list if the DB is unavailable or the table doesn't
        exist yet (e.g., first-run before migration).
        """
        try:
            async with self._session_factory() as session:
                result = await session.execute(_SELECT_HTTP_EXTERNAL_SQL)
                rows = result.mappings().all()

            return [
                _ExternalToolRow(
                    tool_name=row["ToolName"],
                    display_name=row["DisplayName"],
                    description=row["Description"],
                    parameters_schema=_parse_json(row["ParametersSchemaJson"], {}),
                    tags=_parse_json(row["TagsJson"], []),
                    endpoint_url=_normalize_kubernetes_service_url(row["EndpointUrl"]),
                    http_method=row["HttpMethod"],
                    credential_key=row["CredentialKey"],
                    timeout_seconds=float(row["TimeoutSeconds"]),
                    max_retries=int(row["MaxRetries"]),
                )
                for row in rows
                if row["EndpointUrl"]  # safety guard: skip rows with missing endpoint
            ]
        except Exception as exc:
            logger.warning("load_external_tools_failed error=%s", exc)
            return []


# ---------------------------------------------------------------------------
# DbBackedExternalToolLoader
# ---------------------------------------------------------------------------


class DbBackedExternalToolLoader:
    """Loads ``http_external`` tools from the DB and registers them into
    a :class:`~agent_runtime.tools.registry.DynamicToolRegistry`.

    This runs on Python service startup after :meth:`ToolCatalogSyncer.upsert_all`
    has synced builtin tools.  Any ``http_external`` tools defined in the
    management plane are then available for agent function-calling schemas.

    Usage::

        loader = DbBackedExternalToolLoader(syncer)
        await loader.load_and_register(registry)
    """

    def __init__(self, syncer: ToolCatalogSyncer) -> None:
        self._syncer = syncer

    async def load_and_register(self, registry: Any) -> int:
        """Fetch active http_external tools from DB and register them.

        Parameters
        ----------
        registry:
            A :class:`~agent_runtime.tools.registry.DynamicToolRegistry`
            instance (typed as ``Any`` to avoid circular imports).

        Returns the number of tools registered.
        """
        rows = await self._syncer.load_external_tools()
        registered = 0

        for row in rows:
            spec = ToolSpec(
                name=row.tool_name,
                description=row.description,
                parameters_schema=row.parameters_schema,
                tags=frozenset(row.tags) | frozenset({"external"}),
                timeout_seconds=row.timeout_seconds,
                max_retries=row.max_retries,
            )
            config = ExternalToolConfig(
                endpoint_url=row.endpoint_url,
                http_method=row.http_method,
                auth_header="Authorization" if row.credential_key else None,
                credential_key=row.credential_key,
            )
            handler = _DbExternalToolHandler(spec=spec, config=config)
            try:
                registry.register_or_replace(spec, handler)
                registered += 1
                logger.debug("external_tool_registered name=%s", row.tool_name)
            except Exception as exc:
                logger.warning(
                    "external_tool_register_failed name=%s error=%s",
                    row.tool_name,
                    exc,
                )

        if registered:
            logger.info("db_external_tools_registered count=%d", registered)
        return registered


# ---------------------------------------------------------------------------
# Internal: dynamic handler for DB-backed external tools
# ---------------------------------------------------------------------------


class _DbExternalToolHandler(HttpToolHandler):
    """Runtime handler for tools loaded from ``agent_tool_definitions``.

    Unlike subclass-based ``HttpToolHandler`` usage (where `spec` is a
    class attribute), here each instance carries its own spec set in ``__init__``.
    """

    def __init__(self, *, spec: ToolSpec, config: ExternalToolConfig) -> None:
        # Set spec before calling super().__init__ because _validate_spec reads it.
        self.spec = spec  # type: ignore[assignment]
        # bypass super().__init__ validation since spec has 'external' in tags (we add it)
        self._config = config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_json(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _normalize_kubernetes_service_url(endpoint_url: str) -> str:
    """Expand short in-cluster service names into namespace-qualified FQDNs.

    A short host like ``http://aihost-api/...`` only resolves reliably when the
    caller shares the same namespace search path. In AKS, that assumption is too
    brittle for DB-seeded external tool URLs. When the runtime knows its
    namespace, rewrite the host to ``<service>.<namespace>.svc.cluster.local``.
    """
    namespace = (
        os.environ.get("POD_NAMESPACE")
        or os.environ.get("KUBERNETES_NAMESPACE")
        or os.environ.get("NAMESPACE")
    )
    if not namespace:
        return endpoint_url

    parsed = urlsplit(endpoint_url)
    hostname = parsed.hostname
    if not hostname or "." in hostname or hostname.lower() == "localhost":
        return endpoint_url

    fqdn = f"{hostname}.{namespace}.svc.cluster.local"
    if parsed.port is not None:
        fqdn = f"{fqdn}:{parsed.port}"

    return urlunsplit((parsed.scheme, fqdn, parsed.path, parsed.query, parsed.fragment))
