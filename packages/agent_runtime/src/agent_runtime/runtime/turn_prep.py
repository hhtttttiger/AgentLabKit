"""Turn preparation — definition resolution, settings overrides, skill composition.

Extracted from ``engine.py`` to isolate the pre-turn setup logic that is shared
by both ``run_turn()`` and ``stream_turn()``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..config import AgentSettings
from ..contracts.models import (
    AgentTurnRequest,
    AppliedSkillRecord,
)
from ..definition.models import (
    AgentDefinitionSnapshot,
    SkillBindingSnapshot,
    SkillDefinitionSnapshot,
)
from ..skills import SkillBinding, SkillComposer, SkillPromptFragment, SkillRegistry, SkillSpec
from ..tools import ToolBinding

if TYPE_CHECKING:
    from ..definition.loader import AgentDefinitionLoader
    from ..mcp import McpClientManager, McpRegistryBridge
    from ..tools import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PreparedTurn:
    """Shared preparation state for both ``run_turn`` and ``stream_turn``.

    Constructed by :func:`prepare_turn` so that the two entry-points can
    share the same setup logic without duplication.
    """

    definition: AgentDefinitionSnapshot | None
    effective_settings: AgentSettings
    tool_bindings: list[ToolBinding] | None
    auto_tool_names: frozenset[str] | None
    applied_skills: list[AppliedSkillRecord]
    resolved_request: AgentTurnRequest


class TurnPrep:
    """Stateless helper for turn preparation — methods extracted from ``AgentRuntime``."""

    def __init__(
        self,
        *,
        settings: AgentSettings,
        tool_registry: ToolRegistry,
        definition_loader: AgentDefinitionLoader | None = None,
        skill_registry: SkillRegistry | None = None,
        mcp_manager: McpClientManager | None = None,
        mcp_bridge: McpRegistryBridge | None = None,
    ) -> None:
        self.settings = settings
        self.tool_registry = tool_registry
        self.definition_loader = definition_loader
        self._skill_registry = skill_registry or SkillRegistry()
        self._skill_composer = SkillComposer(self._skill_registry)
        self._mcp_manager = mcp_manager
        self._mcp_bridge = mcp_bridge

    async def prepare_turn(self, request: AgentTurnRequest) -> PreparedTurn:
        """Full turn preparation pipeline."""
        definition = await self._resolve_definition(request)
        effective_settings = self._apply_request_overrides(
            self._apply_definition_overrides(definition),
            request,
        )
        await self._ensure_mcp_for_definition(definition)
        tool_bindings = self._resolve_effective_tool_bindings(definition)
        effective_settings, tool_bindings = self._apply_skill_composition(
            definition, effective_settings, tool_bindings
        )
        applied_skills = self._collect_applied_skills(definition)
        auto_tool_names = self._resolve_auto_tool_names(tool_bindings)
        resolved_request = self._normalize_request(request, effective_settings, definition)
        return PreparedTurn(
            definition=definition,
            effective_settings=effective_settings,
            tool_bindings=tool_bindings,
            auto_tool_names=auto_tool_names,
            applied_skills=applied_skills,
            resolved_request=resolved_request,
        )

    # ── Definition resolution ─────────────────────────────────────────────

    async def _resolve_definition(
        self, request: AgentTurnRequest
    ) -> AgentDefinitionSnapshot | None:
        if not request.agent_key or self.definition_loader is None:
            return None
        refresh = getattr(self.definition_loader, "refresh_if_stale", None)
        if callable(refresh):
            await refresh()
        definition = await self.definition_loader.load(
            request.agent_key, request.agent_version
        )
        return definition

    # ── Settings overrides ────────────────────────────────────────────────

    def _apply_definition_overrides(
        self, definition: AgentDefinitionSnapshot | None
    ) -> AgentSettings:
        if definition is None:
            return self.settings
        overrides: dict[str, object] = {}
        if definition.system_prompt_template:
            overrides["default_system_prompt"] = definition.system_prompt_template
        runtime_opts = definition.runtime_options
        if "temperature" in runtime_opts:
            overrides["temperature"] = runtime_opts["temperature"]
        if "max_output_tokens" in runtime_opts:
            overrides["max_output_tokens"] = runtime_opts["max_output_tokens"]
        if "max_history_messages" in runtime_opts:
            overrides["max_history_messages"] = runtime_opts["max_history_messages"]
        handoff_opts = definition.handoff_policy
        if "enabled" in handoff_opts:
            overrides["enable_handoff_policy"] = handoff_opts["enabled"]
        if "default_message" in handoff_opts:
            overrides["default_handoff_message"] = handoff_opts["default_message"]
        return self.settings.model_copy(update=overrides) if overrides else self.settings

    @staticmethod
    def _apply_request_overrides(
        settings: AgentSettings,
        request: AgentTurnRequest,
    ) -> AgentSettings:
        if not request.agent_runtime_overrides:
            return settings
        parsed: dict[str, object] = {}
        for key, value in request.agent_runtime_overrides.items():
            if key == "temperature":
                parsed[key] = float(value)
            elif key in {"max_output_tokens", "max_history_messages"}:
                parsed[key] = int(value)
            elif key == "enable_handoff_policy":
                parsed[key] = value.strip().lower() in {"1", "true", "yes", "on"}
            elif key == "default_handoff_message":
                parsed[key] = value
        return settings.model_copy(update=parsed) if parsed else settings

    # ── Request normalization ─────────────────────────────────────────────

    @staticmethod
    def _normalize_request(
        request: AgentTurnRequest,
        settings: AgentSettings,
        definition: AgentDefinitionSnapshot | None,
    ) -> AgentTurnRequest:
        from uuid import uuid4

        default_model = (
            definition.model_binding_key
            if definition and definition.model_binding_key
            else settings.default_model
        )
        return request.model_copy(
            update={
                "model": request.model if (request.model and not request.agent_key) else default_model,
                "provider": request.provider if not request.agent_key else None,
                "trace_id": request.trace_id or str(uuid4()),
                "metadata": dict(request.metadata),
                "history": list(request.history),
                "knowledge_chunks": list(request.knowledge_chunks),
                "knowledge_lookup_status": request.knowledge_lookup_status,
            }
        )

    # ── Tool binding resolution ───────────────────────────────────────────

    @staticmethod
    def _resolve_tool_bindings(
        definition: AgentDefinitionSnapshot | None,
    ) -> list[ToolBinding] | None:
        if definition is None:
            return None
        from ..tools.contracts import binding_from_snapshot

        return [binding_from_snapshot(t) for t in definition.tools]

    def _resolve_effective_tool_bindings(
        self,
        definition: AgentDefinitionSnapshot | None,
    ) -> list[ToolBinding] | None:
        bindings = self._resolve_tool_bindings(definition)
        if bindings is None or definition is None:
            return bindings
        seen = {binding.tool_name for binding in bindings}
        for binding in self._resolve_mcp_tool_bindings(definition):
            if binding.tool_name in seen:
                continue
            bindings.append(binding)
            seen.add(binding.tool_name)
        return bindings

    @staticmethod
    def _resolve_auto_tool_names(
        tool_bindings: list[ToolBinding] | None,
    ) -> frozenset[str] | None:
        if tool_bindings is None:
            return None
        return frozenset(
            binding.tool_name
            for binding in tool_bindings
            if binding.is_enabled and binding.invocation_mode == "auto"
        )

    def _resolve_mcp_tool_bindings(
        self,
        definition: AgentDefinitionSnapshot,
    ) -> list[ToolBinding]:
        if not definition.mcp_bindings:
            return []
        registered_specs = self.tool_registry.dynamic_registry.list_all()
        bindings: list[ToolBinding] = []
        for snapshot in definition.mcp_bindings:
            if not snapshot.is_enabled:
                continue
            config_json = snapshot.server_config_json
            prefix = config_json.get("tool_name_prefix")
            if not isinstance(prefix, str) or not prefix:
                prefix = None
            server_tag = f"mcp:{snapshot.server_name}"
            if snapshot.tool_whitelist is None:
                tool_names = [
                    spec.name for spec in registered_specs if server_tag in spec.tags
                ]
            else:
                allowed = {
                    self._resolve_mcp_tool_name(raw_name, prefix)
                    for raw_name in snapshot.tool_whitelist
                }
                tool_names = [
                    spec.name
                    for spec in registered_specs
                    if server_tag in spec.tags and spec.name in allowed
                ]
            bindings.extend(
                ToolBinding(tool_name=tool_name, invocation_mode="auto")
                for tool_name in tool_names
            )
        return bindings

    @staticmethod
    def _resolve_mcp_tool_name(raw_name: str, prefix: str | None) -> str:
        if not prefix:
            return raw_name
        if raw_name.startswith(prefix):
            return raw_name
        return f"{prefix}{raw_name}"

    # ── MCP definition sync ───────────────────────────────────────────────

    async def _ensure_mcp_for_definition(
        self, definition: AgentDefinitionSnapshot | None
    ) -> None:
        if (
            definition is None
            or not definition.mcp_bindings
            or self._mcp_manager is None
            or self._mcp_bridge is None
        ):
            return

        from ..mcp.contracts import McpServerBinding, McpServerConfig

        configs: list[McpServerConfig] = []
        bindings: list[McpServerBinding] = []
        for snap in definition.mcp_bindings:
            if not snap.is_enabled:
                continue
            try:
                config = McpServerConfig.model_validate(snap.server_config_json)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "mcp_definition_config_invalid agent=%s server=%s error=%s",
                    definition.agent_key,
                    snap.server_name,
                    exc,
                )
                continue
            await self._mcp_manager.ensure_server(config)
            configs.append(config)
            bindings.append(
                McpServerBinding(
                    server_name=snap.server_name,
                    is_enabled=True,
                    tool_whitelist=(
                        list(snap.tool_whitelist)
                        if snap.tool_whitelist is not None
                        else None
                    ),
                )
            )
        if configs:
            await self._mcp_bridge.sync_all(configs=configs, bindings=bindings)

    # ── Skill composition ─────────────────────────────────────────────────

    def _apply_skill_composition(
        self,
        definition: AgentDefinitionSnapshot | None,
        settings: AgentSettings,
        tool_bindings: list[ToolBinding] | None,
    ) -> tuple[AgentSettings, list[ToolBinding] | None]:
        if definition is None or not definition.skill_bindings:
            return settings, tool_bindings

        from ..tools.contracts import binding_from_snapshot as _binding_from_snapshot

        composer = self._skill_composer_for_definition(definition)
        skill_bindings = [
            _snapshot_to_skill_binding(snap) for snap in definition.skill_bindings
        ]
        composed_prompt = composer.compose_prompt(
            settings.default_system_prompt, skill_bindings
        )
        if composed_prompt != settings.default_system_prompt:
            settings = settings.model_copy(
                update={"default_system_prompt": composed_prompt}
            )
        if tool_bindings is not None:
            tool_bindings = composer.compose_tool_bindings(tool_bindings, skill_bindings)
        return settings, tool_bindings

    def _skill_composer_for_definition(
        self, definition: AgentDefinitionSnapshot
    ) -> SkillComposer:
        definition_specs = [
            _skill_spec_from_snapshot(binding.definition)
            for binding in definition.skill_bindings
            if binding.definition is not None
        ]
        resolved_specs = [spec for spec in definition_specs if spec is not None]
        if not resolved_specs:
            return self._skill_composer
        registry = SkillRegistry()
        for spec in self._skill_registry.list_all():
            registry.register(spec)
        for spec in resolved_specs:
            registry.register(spec)
        return SkillComposer(registry)

    @staticmethod
    def _collect_applied_skills(
        definition: AgentDefinitionSnapshot | None,
    ) -> list[AppliedSkillRecord]:
        if definition is None or not definition.skill_bindings:
            return []
        applied: list[AppliedSkillRecord] = []
        for binding in sorted(definition.skill_bindings, key=lambda item: item.binding_order):
            if not binding.is_enabled:
                continue
            display_name = (
                binding.definition.display_name
                if binding.definition is not None
                else binding.skill_key
            )
            applied.append(
                AppliedSkillRecord(
                    skill_key=binding.skill_key,
                    display_name=display_name,
                    order=binding.binding_order,
                    config=dict(binding.config or {}),
                )
            )
        return applied


# ── Skill helper functions (module-level) ─────────────────────────────────


def _snapshot_to_skill_binding(snap: SkillBindingSnapshot) -> SkillBinding:
    from .engine import _tool_binding_from_dict

    tool_overrides: list[ToolBinding] = []
    for raw_override in snap.tool_overrides_raw:
        try:
            tool_overrides.append(_tool_binding_from_dict(raw_override))
        except (KeyError, TypeError, ValueError):
            logger.warning(
                "skill_binding_skip_invalid_tool_override skill=%s raw=%s",
                snap.skill_key,
                raw_override,
            )
    return SkillBinding(
        skill_key=snap.skill_key,
        is_enabled=snap.is_enabled,
        order=snap.binding_order,
        config=dict(snap.config or {}),
        tool_overrides=tuple(tool_overrides),
    )


def _skill_spec_from_snapshot(
    snapshot: SkillDefinitionSnapshot | None,
) -> SkillSpec | None:
    if snapshot is None:
        return None

    def _get(raw: dict, snake_key: str, camel_key: str):
        if snake_key in raw:
            return raw[snake_key]
        return raw.get(camel_key)

    raw_fragments = _get(snapshot.spec, "prompt_fragments", "promptFragments") or []
    prompt_fragments: list[SkillPromptFragment] = []
    for raw_fragment in raw_fragments:
        if not isinstance(raw_fragment, dict):
            continue
        section = str(raw_fragment.get("section") or "").strip()
        content = str(raw_fragment.get("content") or "")
        if not section or not content:
            continue
        prompt_fragments.append(
            SkillPromptFragment(
                section=section,
                content=content,
                order=int(raw_fragment.get("order", 100)),
                is_required=bool(
                    _get(raw_fragment, "is_required", "isRequired")
                    if _get(raw_fragment, "is_required", "isRequired") is not None
                    else True
                ),
            )
        )
    raw_tools = _get(snapshot.spec, "recommended_tools", "recommendedTools") or ()
    recommended_tools = tuple(
        str(tool_name)
        for tool_name in raw_tools
        if isinstance(tool_name, str) and tool_name.strip()
    )
    raw_tags = snapshot.spec.get("tags") or ()
    tags = frozenset(
        str(tag) for tag in raw_tags if isinstance(tag, str) and tag.strip()
    )
    return SkillSpec(
        skill_key=snapshot.skill_key,
        display_name=snapshot.display_name,
        description=snapshot.description,
        version=snapshot.version,
        prompt_fragments=tuple(prompt_fragments),
        recommended_tools=recommended_tools,
        config_schema=dict(_get(snapshot.spec, "config_schema", "configSchema") or {}),
        tags=tags,
    )


__all__ = ["PreparedTurn", "TurnPrep"]
