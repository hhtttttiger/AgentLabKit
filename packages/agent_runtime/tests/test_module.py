from __future__ import annotations

from unittest.mock import Mock, patch



from agent_runtime.config import AgentSettings, MemorySettings
from agent_runtime.mcp import McpClientManager
from agent_runtime.module import create_agent_module, load_agent_module
from agent_runtime.orchestration import HandoffManager
from agent_runtime.skills import SkillRegistry
from agent_runtime.skills.builtin import CustomerSupportSkill, RagQaSkill
from agent_runtime.tools import ToolRegistry
from llm_gateway import GatewayModule


class TestAgentModule:
    def test_create_agent_module_accepts_gateway_module(self):
        gateway_service = Mock()
        gateway_module = GatewayModule(settings=Mock(), service=gateway_service)

        module = create_agent_module(
            settings=AgentSettings(),
            gateway=gateway_module,
            tool_registry=ToolRegistry(),
        )

        assert module.gateway is gateway_service
        assert module.runtime.gateway is gateway_service

    def test_load_agent_module_uses_default_gateway_loader(self):
        gateway_service = Mock()
        gateway_module = GatewayModule(settings=Mock(), service=gateway_service)

        with patch("agent_runtime.runtime.factory.load_gateway_module", return_value=gateway_module):
            module = load_agent_module()

        assert module.gateway is gateway_service

    def test_create_agent_module_builds_memory_components_when_enabled(self):
        gateway_service = Mock()
        gateway_module = GatewayModule(settings=Mock(), service=gateway_service)

        module = create_agent_module(
            settings=AgentSettings(
                memory=MemorySettings(
                    enabled=True,
                    persist_sessions=True,
                )
            ),
            gateway=gateway_module,
            tool_registry=ToolRegistry(),
        )

        assert module.context_manager is not None
        assert module.session_store is not None
        assert module.runtime.context_manager is module.context_manager

    def test_create_agent_module_builds_mcp_manager_from_settings(self):
        gateway_service = Mock()
        gateway_module = GatewayModule(settings=Mock(), service=gateway_service)

        module = create_agent_module(
            settings=AgentSettings(
                enable_mcp=True,
                mcp_servers=[
                    {"name": "fs", "transport": "stdio", "command": "npx"}
                ],
            ),
            gateway=gateway_module,
            tool_registry=ToolRegistry(),
        )

        assert isinstance(module.runtime._mcp_manager, McpClientManager)
        assert [config.name for config in module.runtime._mcp_manager.list_configs()] == ["fs"]

    def test_create_agent_module_accepts_explicit_skill_registry(self):
        gateway_service = Mock()
        gateway_module = GatewayModule(settings=Mock(), service=gateway_service)
        skill_registry = SkillRegistry()

        module = create_agent_module(
            settings=AgentSettings(),
            gateway=gateway_module,
            tool_registry=ToolRegistry(),
            skill_registry=skill_registry,
        )

        assert module.runtime._skill_registry is skill_registry

    def test_create_agent_module_accepts_explicit_handoff_manager(self):
        gateway_service = Mock()
        gateway_module = GatewayModule(settings=Mock(), service=gateway_service)
        handoff_manager = HandoffManager(Mock())

        module = create_agent_module(
            settings=AgentSettings(),
            gateway=gateway_module,
            tool_registry=ToolRegistry(),
            handoff_manager=handoff_manager,
        )

        assert module.runtime._handoff_manager is handoff_manager
        assert module.handoff_manager is handoff_manager

    def test_create_agent_module_registers_builtin_skills_by_default(self):
        gateway_service = Mock()
        gateway_module = GatewayModule(settings=Mock(), service=gateway_service)

        module = create_agent_module(
            settings=AgentSettings(),
            gateway=gateway_module,
            tool_registry=ToolRegistry(),
        )

        assert module.runtime._skill_registry.get(RagQaSkill.spec.skill_key) == RagQaSkill.spec
        assert (
            module.runtime._skill_registry.get(CustomerSupportSkill.spec.skill_key)
            == CustomerSupportSkill.spec
        )
