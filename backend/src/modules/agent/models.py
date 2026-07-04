from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from alkit_db.base import EntityBase


class AgentDefinition(EntityBase):
    __tablename__ = "agent_definitions"

    agent_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(String(1024))
    icon: Mapped[str | None] = mapped_column(String(64))
    tags_json: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    published_version: Mapped[int | None] = mapped_column(BigInteger, default=None)


class AgentDefinitionVersion(EntityBase):
    __tablename__ = "agent_definition_versions"

    agent_id: Mapped[int] = mapped_column(BigInteger, index=True)
    version_number: Mapped[int] = mapped_column(BigInteger)
    system_prompt: Mapped[str | None] = mapped_column(Text)
    model_binding_key: Mapped[str | None] = mapped_column(String(128))
    temperature: Mapped[float | None] = mapped_column()
    max_tokens: Mapped[int | None] = mapped_column(Integer)
    response_format: Mapped[str | None] = mapped_column(String(32))
    extra_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    checksum: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (
        Index("ix_agent_version_agent_ver", "agent_id", "version_number"),
    )


class AgentTool(EntityBase):
    __tablename__ = "agent_tools"

    tool_name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(String(1024))
    parameters_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    source: Mapped[str] = mapped_column(String(32), default="external")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    tags_json: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    endpoint_url: Mapped[str | None] = mapped_column(String(2048))
    http_method: Mapped[str] = mapped_column(String(8), default="POST")
    credential_key: Mapped[str | None] = mapped_column(String(256))
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)
    max_retries: Mapped[int] = mapped_column(Integer, default=0)


class AgentToolBinding(EntityBase):
    __tablename__ = "agent_tool_bindings"

    agent_version_id: Mapped[int] = mapped_column(BigInteger, index=True)
    tool_name: Mapped[str] = mapped_column(String(128), index=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    extra_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    __table_args__ = (
        UniqueConstraint("agent_version_id", "tool_name", name="uq_agent_tool_binding"),
    )


class AgentSkill(EntityBase):
    __tablename__ = "agent_skills"

    skill_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(String(1024))
    content: Mapped[str] = mapped_column(Text)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)


class AgentSkillBinding(EntityBase):
    __tablename__ = "agent_skill_bindings"

    agent_version_id: Mapped[int] = mapped_column(BigInteger, index=True)
    skill_key: Mapped[str] = mapped_column(String(128), index=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    extra_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    __table_args__ = (
        UniqueConstraint("agent_version_id", "skill_key", name="uq_agent_skill_binding"),
    )


class AgentMcpServer(EntityBase):
    __tablename__ = "agent_mcp_servers"

    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(256))
    transport_type: Mapped[str] = mapped_column(String(32))
    url: Mapped[str | None] = mapped_column(String(1024))
    command: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    args_json: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    headers_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class AgentMcpBinding(EntityBase):
    __tablename__ = "agent_mcp_bindings"

    agent_version_id: Mapped[int] = mapped_column(BigInteger, index=True)
    server_name: Mapped[str] = mapped_column(String(128), index=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    extra_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    __table_args__ = (
        UniqueConstraint("agent_version_id", "server_name", name="uq_agent_mcp_binding"),
    )


class AgentKnowledgeBaseBinding(EntityBase):
    __tablename__ = "agent_knowledge_base_bindings"

    agent_version_id: Mapped[int] = mapped_column(BigInteger, index=True)
    knowledge_base_id: Mapped[int] = mapped_column(BigInteger, index=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    extra_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    __table_args__ = (
        UniqueConstraint("agent_version_id", "knowledge_base_id", name="uq_agent_kb_binding"),
    )


class AgentCatalogRevision(EntityBase):
    __tablename__ = "agent_catalog_revisions"

    revision: Mapped[int] = mapped_column(BigInteger, unique=True)


class AgentExecutionAudit(EntityBase):
    __tablename__ = "agent_execution_audits"

    agent_key: Mapped[str] = mapped_column(String(128), index=True)
    run_id: Mapped[str] = mapped_column(String(128), index=True)
    agent_version: Mapped[int | None] = mapped_column(BigInteger)
    input_summary: Mapped[str | None] = mapped_column(Text)
    output_summary: Mapped[str | None] = mapped_column(Text)
    tool_calls_json: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    status: Mapped[str] = mapped_column(String(32), default="success")
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)
    token_usage_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    error_message: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_agent_audit_key_time", "agent_key", "created_at_utc"),
    )

