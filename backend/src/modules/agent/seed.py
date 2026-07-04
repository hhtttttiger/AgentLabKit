"""Seed default agent definition with model binding.

Idempotent — skips records that already exist (matched by unique keys).

Usage:
    from modules.agent.seed import seed_agent
    await seed_agent(session)
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from alkit_db.llm_catalog import LlmModel, LlmModelBinding
from .models import (
    AgentDefinition,
    AgentDefinitionVersion,
    AgentMcpBinding,
    AgentMcpServer,
    AgentSkill,
    AgentSkillBinding,
    AgentToolBinding,
)


async def seed_agent(session: AsyncSession) -> None:
    """Seed default agent (idempotent)."""

    # 1. Default agent
    binding_key = "mimo-v2.5"
    agent_key = "default"
    existing_agent = await session.execute(
        select(AgentDefinition).where(AgentDefinition.agent_key == agent_key)
    )
    agent = existing_agent.scalar_one_or_none()
    if agent is None:
        agent = AgentDefinition(
            agent_key=agent_key,
            display_name="默认助手",
            description="系统默认 Agent，绑定 MiMo V2.5 模型",
            is_enabled=True,
        )
        session.add(agent)
        await session.flush()

    # 2. Version 1 (skip if already exists)
    existing_ver = await session.execute(
        select(AgentDefinitionVersion).where(
            AgentDefinitionVersion.agent_id == agent.id,
            AgentDefinitionVersion.version_number == 1,
        )
    )
    if existing_ver.scalar_one_or_none() is None:
        ver = AgentDefinitionVersion(
            agent_id=agent.id,
            version_number=1,
            system_prompt="你是一个有用的AI助手。",
            model_binding_key=binding_key,
            temperature=0.7,
            max_tokens=4096,
        )
        session.add(ver)
        await session.flush()
        agent.published_version = 1
        await session.flush()


async def seed_clock_agent(session: AsyncSession) -> None:
    """Seed a demo agent that binds the built-in ``time_now`` tool (idempotent).

    Exists to exercise the tool-execution loop end-to-end without retrieval:
    asking it the time should drive the LLM to call ``time_now``, surfacing
    ``tool_call`` / ``tool_result`` in the trace. Requires
    :func:`modules.agent.builtin_tools.register_builtin_tools` to have
    registered ``time_now`` into the runtime registry (done at startup).
    """

    binding_key = "mimo-v2.5"

    agent_key = "clock"
    agent = (
        await session.execute(
            select(AgentDefinition).where(AgentDefinition.agent_key == agent_key)
        )
    ).scalar_one_or_none()
    if agent is None:
        agent = AgentDefinition(
            agent_key=agent_key,
            display_name="时钟助手",
            description="Demo agent — 绑定 time_now 工具，用于验证工具执行闭环",
            is_enabled=True,
        )
        session.add(agent)
        await session.flush()

    # Version 1 (skip if already exists)
    ver = (
        await session.execute(
            select(AgentDefinitionVersion).where(
                AgentDefinitionVersion.agent_id == agent.id,
                AgentDefinitionVersion.version_number == 1,
            )
        )
    ).scalar_one_or_none()
    if ver is None:
        ver = AgentDefinitionVersion(
            agent_id=agent.id,
            version_number=1,
            system_prompt=(
                "你是一个时钟助手。当用户询问当前时间、日期或时间戳时，"
                "必须先调用 time_now 工具获取时间，再用工具返回的结果作答。"
                "不要凭记忆猜测时间。"
            ),
            model_binding_key=binding_key,
            temperature=0.2,
            max_tokens=1024,
        )
        session.add(ver)
        await session.flush()
        agent.published_version = 1
        await session.flush()

    # Bind time_now to this version (skip if already bound)
    existing_binding = await session.execute(
        select(AgentToolBinding).where(
            AgentToolBinding.agent_version_id == ver.id,
            AgentToolBinding.tool_name == "time_now",
        )
    )
    if existing_binding.scalar_one_or_none() is None:
        session.add(
            AgentToolBinding(
                agent_version_id=ver.id,
                tool_name="time_now",
                is_enabled=True,
                extra_json={"invocation_mode": "auto"},
            )
        )
        await session.flush()


async def seed_mcp_demo(session: AsyncSession) -> None:
    """Seed an MCP demo agent that connects to a real stdio MCP time server.

    Creates:
    - MCP server config ``time`` (``alans-date-time-mcp`` via stdio transport)
    - Agent ``mcp-demo`` with an MCP binding to ``time``
    - Published version 1

    Prerequisite: ``alans-date-time-mcp`` must be installed globally
    (``npm install -g alans-date-time-mcp``).  Without it the MCP connection
    will fail at runtime, but the agent definition is still seedable.

    Idempotent — skips records that already exist (matched by unique keys).
    Requires ``seed_agent`` to have run first (for the ``mimo-v2.5`` model).
    """

    binding_key = "mimo-v2.5"

    # 1. MCP server config (idempotent by unique name)
    server_name = "time"
    existing_server = await session.execute(
        select(AgentMcpServer).where(AgentMcpServer.name == server_name)
    )
    if existing_server.scalar_one_or_none() is None:
        session.add(
            AgentMcpServer(
                name=server_name,
                display_name="Time Server (MCP)",
                transport_type="stdio",
                command="alans-date-time-mcp",
                args_json=[],
                is_enabled=True,
            )
        )
        await session.flush()

    # 2. Agent definition (idempotent by unique agent_key)
    agent_key = "mcp-demo"
    agent = (
        await session.execute(
            select(AgentDefinition).where(AgentDefinition.agent_key == agent_key)
        )
    ).scalar_one_or_none()
    if agent is None:
        agent = AgentDefinition(
            agent_key=agent_key,
            display_name="MCP Demo",
            description=(
                "MCP 集成示例 Agent — 通过 stdio transport 连接 "
                "alans-date-time-mcp 服务，可调用 get_time / get_date / get_datetime 工具"
            ),
            is_enabled=True,
        )
        session.add(agent)
        await session.flush()

    # 3. Version 1 (skip if already exists)
    ver = (
        await session.execute(
            select(AgentDefinitionVersion).where(
                AgentDefinitionVersion.agent_id == agent.id,
                AgentDefinitionVersion.version_number == 1,
            )
        )
    ).scalar_one_or_none()
    if ver is None:
        ver = AgentDefinitionVersion(
            agent_id=agent.id,
            version_number=1,
            system_prompt=(
                "You are a helpful assistant with access to time tools via MCP. "
                "When the user asks about the current time, date, or datetime, "
                "you MUST call the appropriate tool: get_time, get_date, or get_datetime. "
                "These tools support an optional 'timezone' parameter (e.g. 'local', 'UTC', 'America/New_York'). "
                "Always use the tool result in your reply — never guess the time."
            ),
            model_binding_key=binding_key,
            temperature=0.2,
            max_tokens=1024,
        )
        session.add(ver)
        await session.flush()
        agent.published_version = 1
        await session.flush()

    # 4. MCP binding (skip if already bound)
    existing_binding = await session.execute(
        select(AgentMcpBinding).where(
            AgentMcpBinding.agent_version_id == ver.id,
            AgentMcpBinding.server_name == server_name,
        )
    )
    if existing_binding.scalar_one_or_none() is None:
        session.add(
            AgentMcpBinding(
                agent_version_id=ver.id,
                server_name=server_name,
                is_enabled=True,
            )
        )
        await session.flush()


async def seed_skill_demo(session: AsyncSession) -> None:
    """Seed a demo skill and an agent bound to it (idempotent).

    Creates:
    - Skill ``demo-skill`` — "步骤分解助手" with structured prompt fragments
      that instruct the LLM to answer in numbered steps with emoji.
    - Agent ``skill-demo`` — bound to the demo skill with custom config
      that demonstrates the ``{config.KEY}`` template variable system.

    This exercises the full skill pipeline: DB → definition loader →
    SkillComposer → system prompt assembly.
    """

    import json as _json

    binding_key = "mimo-v2.5"

    # 1. Skill definition (idempotent by unique skill_key)
    skill_key = "demo-skill"
    existing_skill = await session.execute(
        select(AgentSkill).where(AgentSkill.skill_key == skill_key)
    )
    if existing_skill.scalar_one_or_none() is None:
        skill_content = _json.dumps(
            {
                "version": "1.0.0",
                "prompt_fragments": [
                    {
                        "section": "📋 步骤分解指令",
                        "content": (
                            "在回答用户问题时，请严格遵循以下规则：\n"
                            "1. **理解确认**：用一句话重述用户的问题，确认你理解了意图。\n"
                            "2. **分步解答**：将回答分解为清晰的步骤，每步用数字序号标注，"
                            "每步包含具体的操作或解释。\n"
                            "3. **补充建议**：如果适用，提供 1-2 条相关的实用建议。\n"
                            "4. **要点总结**：在回答末尾用「💡 关键要点」标题总结 2-3 个核心信息。\n\n"
                            "{config.custom_instruction}"
                        ),
                        "order": 10,
                    },
                    {
                        "section": "🎨 表达风格",
                        "content": (
                            "请使用专业但友好的语气进行交流。在适当位置使用emoji增强可读性"
                            "（但不要过度使用）。回答应简洁、有条理，避免冗余表述。"
                            "优先使用中文回答，除非用户使用其他语言提问。"
                        ),
                        "order": 20,
                    },
                ],
                "recommended_tools": [],
                "tags": ["demo", "instruction-following", "step-by-step"],
            },
            ensure_ascii=False,
        )
        session.add(
            AgentSkill(
                skill_key=skill_key,
                display_name="步骤分解助手技能",
                description=(
                    "演示技能 — 为 Agent 注入结构化分步回答能力。"
                    "包含步骤分解指令和表达风格指导，支持 {config.custom_instruction} 模板变量。"
                ),
                content=skill_content,
                is_published=True,
            )
        )
        await session.flush()

    # 2. Agent definition (idempotent by unique agent_key)
    agent_key = "skill-demo"
    agent = (
        await session.execute(
            select(AgentDefinition).where(AgentDefinition.agent_key == agent_key)
        )
    ).scalar_one_or_none()
    if agent is None:
        agent = AgentDefinition(
            agent_key=agent_key,
            display_name="技能演示助手",
            description=(
                "Skills 集成示例 Agent — 绑定「步骤分解助手技能」，"
                "验证技能系统端到端流程：技能定义 → 绑定 → 提示词组合"
            ),
            is_enabled=True,
        )
        session.add(agent)
        await session.flush()

    # 3. Version 1 (skip if already exists)
    ver = (
        await session.execute(
            select(AgentDefinitionVersion).where(
                AgentDefinitionVersion.agent_id == agent.id,
                AgentDefinitionVersion.version_number == 1,
            )
        )
    ).scalar_one_or_none()
    if ver is None:
        ver = AgentDefinitionVersion(
            agent_id=agent.id,
            version_number=1,
            system_prompt=(
                "你是一个乐于助人的AI助手。你擅长将复杂问题分解为清晰的步骤，"
                "并用有条理的方式呈现答案。"
            ),
            model_binding_key=binding_key,
            temperature=0.7,
            max_tokens=4096,
        )
        session.add(ver)
        await session.flush()
        agent.published_version = 1
        await session.flush()

    # 4. Skill binding (skip if already bound)
    existing_binding = await session.execute(
        select(AgentSkillBinding).where(
            AgentSkillBinding.agent_version_id == ver.id,
            AgentSkillBinding.skill_key == skill_key,
        )
    )
    if existing_binding.scalar_one_or_none() is None:
        session.add(
            AgentSkillBinding(
                agent_version_id=ver.id,
                skill_key=skill_key,
                is_enabled=True,
                extra_json={
                    "binding_order": 100,
                    "config": {
                        "custom_instruction": (
                            "另外，如果用户的问题是开放式的，请在步骤分解后"
                            "主动询问用户是否需要更详细的解释。"
                        ),
                    },
                },
            )
        )
        await session.flush()
