from __future__ import annotations

from pydantic import Field

from common.schemas import CamelModel


class AgentCreate(CamelModel):
    agent_key: str
    display_name: str
    description: str | None = None
    icon: str | None = None
    tags_json: list = []
    is_enabled: bool = True


class AgentUpdate(CamelModel):
    display_name: str | None = None
    description: str | None = None
    icon: str | None = None
    tags_json: list | None = None
    is_enabled: bool | None = None
    row_version: float | None = None


# ── Binding sub-schemas (unified version create/update) ──────────────────────


class ToolBindingItem(CamelModel):
    tool_name: str = ""
    display_name: str | None = None
    description: str | None = None
    invocation_mode: str = "auto"
    is_required: bool = False
    config: dict = {}
    sort_order: int = 0
    is_enabled: bool = True


class KbBindingItem(CamelModel):
    knowledge_base_id: str = ""  # frontend sends string
    sort_order: int = 0
    is_enabled: bool = True
    config: dict = {}


class McpBindingItem(CamelModel):
    server_name: str = ""
    is_enabled: bool = True
    tool_whitelist: list | None = None
    config_overrides: dict = {}


class SkillBindingItem(CamelModel):
    skill_key: str = ""
    is_enabled: bool = True
    binding_order: int = 0
    config: dict = {}
    tool_overrides: list | None = None


class VersionCreate(CamelModel):
    # Field names mirror the frontend editor contract; CamelModel's
    # alias_generator turns each snake_case name into the matching camelCase
    # alias (system_prompt_template -> systemPromptTemplate, model_key -> modelKey,
    # runtime_options -> runtimeOptions, ...). The service layer maps these
    # onto DB columns + a structured extra_json blob.
    system_prompt_template: str = ""
    model_key: str = ""
    version_label: str | None = None
    change_summary: str | None = None
    default_locale: str | None = None
    runtime_options: dict | None = None
    handoff_policy: dict | None = None
    response_policy: dict | None = None
    guardrails_policy: dict | None = None
    # Back-compat scalar knobs (still real columns; the current editor does not
    # send them, but they remain accepted/persisted).
    temperature: float | None = None
    max_tokens: int | None = None
    response_format: str | None = None
    # Bindings — all in one request
    tool_bindings: list[ToolBindingItem] = []
    knowledge_base_bindings: list[KbBindingItem] = []
    mcp_bindings: list[McpBindingItem] = []
    skill_bindings: list[SkillBindingItem] = []


class ToolBindingCreate(CamelModel):
    tool_name: str
    is_enabled: bool = True
    extra_json: dict = {}


class KbBindingCreate(CamelModel):
    knowledge_base_id: int
    is_enabled: bool = True


class ToolDefCreate(CamelModel):
    tool_name: str
    display_name: str
    description: str | None = None
    parameters_json: dict = Field(default={}, alias="parametersSchema")
    tags_json: list = Field(default=[], alias="tags")
    endpoint_url: str = ""
    http_method: str = "POST"
    credential_key: str | None = None
    timeout_seconds: int = 30
    max_retries: int = 0


class ToolDefUpdate(CamelModel):
    display_name: str | None = None
    description: str | None = None
    parameters_json: dict | None = Field(default=None, alias="parametersSchema")
    tags_json: list | None = Field(default=None, alias="tags")
    endpoint_url: str | None = None
    http_method: str | None = None
    credential_key: str | None = None
    timeout_seconds: int | None = None
    max_retries: int | None = None
    status: str | None = None


class SkillDefCreate(CamelModel):
    skill_key: str
    display_name: str
    description: str | None = None
    content: str = ""


class SkillDefUpdate(CamelModel):
    display_name: str | None = None
    description: str | None = None
    content: str | None = None


class McpConfigCreate(CamelModel):
    name: str
    display_name: str
    transport_type: str = "sse"
    url: str | None = None
    command: str | None = None
    args_json: list = []
    headers_json: dict = {}
    is_enabled: bool = True


class McpConfigUpdate(CamelModel):
    display_name: str | None = None
    transport_type: str | None = None
    url: str | None = None
    command: str | None = None
    args_json: list | None = None
    headers_json: dict | None = None
    is_enabled: bool | None = None


class PublishAgentRequest(CamelModel):
    version_number: int | None = None
    definition_row_version: float | None = None
    version_row_version: float | None = None


class DisableAgentRequest(CamelModel):
    reason: str | None = None
    row_version: float | None = None
