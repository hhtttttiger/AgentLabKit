export type { PagedResult as AgentPagedResult } from '@/shared/types/paging';

// ── Enums ──

export type AgentStatus = 'draft' | 'published' | 'disabled';
export type VersionStatus = 'draft' | 'published' | 'archived';
export type InvocationMode = 'auto' | 'manual_only' | 'disabled';
export type AgentLocalGuardrailsPolicy = Record<string, unknown>;

// ── Agent Definition ──

export type AgentSummaryView = {
  agentKey: string;
  displayName: string;
  description: string | null;
  status: AgentStatus;
  publishedVersionNumber: number | null;
  rowVersion: number;
  createdAtUtc: string;
  updatedAtUtc: string | null;
};

export type AgentVersionSummaryView = {
  versionNumber: number;
  versionStatus: VersionStatus;
  versionLabel: string | null;
  changeSummary: string | null;
  modelKey: string;
  checksum: string | null;
  rowVersion: number;
  publishedAtUtc: string | null;
  createdAtUtc: string;
};

export type AgentDetailView = AgentSummaryView & {
  tags: string[];
  metadata: Record<string, unknown>;
  publishedVersion: AgentVersionSummaryView | null;
};

export type CreateAgentRequest = {
  agentKey: string;
  displayName: string;
  description: string | null;
  tags: string[];
  metadata: Record<string, unknown>;
};

export type UpdateAgentRequest = {
  displayName: string;
  description: string | null;
  tags: string[];
  metadata: Record<string, unknown>;
  rowVersion: number;
};

export type AgentListQuery = {
  status?: AgentStatus;
  page: number;
  pageSize: number;
};

// ── Agent Version ──

export type ToolBindingView = {
  toolName: string;
  displayName: string | null;
  description: string | null;
  invocationMode: InvocationMode;
  isRequired: boolean;
  config: Record<string, unknown>;
  sortOrder: number;
  isEnabled: boolean;
};

// ── MCP Bindings ──

export type McpBindingView = {
  id: string;
  serverName: string;
  toolWhitelist: string[] | null;
  isEnabled: boolean;
  configOverrides: Record<string, unknown>;
};

export type McpBindingWriteModel = {
  serverName: string;
  toolWhitelist: string[] | null;
  isEnabled: boolean;
};

export type VersionMcpBindingRequest = {
  serverName: string;
  isEnabled: boolean;
  toolWhitelist: string[] | null;
  configOverrides: Record<string, unknown>;
};

export type KnowledgeBaseBindingWriteModel = {
  id: string | null;
  knowledgeBaseId: string;
  sortOrder: number;
  isEnabled: boolean;
  config: Record<string, unknown>;
};

export type VersionKnowledgeBaseBindingRequest = {
  knowledgeBaseId: string;
  sortOrder: number;
  isEnabled: boolean;
  config: Record<string, unknown>;
};

// ── Skill Bindings ──

export type SkillBindingWriteModel = {
  skillKey: string;
  configOverrides: Record<string, unknown>;
  toolOverrides: ToolBindingWriteModel[];
  sortOrder: number;
  isEnabled: boolean;
};

export type VersionSkillBindingRequest = {
  skillKey: string;
  isEnabled: boolean;
  bindingOrder: number;
  config: Record<string, unknown>;
  toolOverrides: ToolBindingWriteModel[] | null;
};

export type KnowledgeBaseBindingView = {
  id: string;
  knowledgeBaseId: string;
  isEnabled: boolean;
  sortOrder: number;
  config: Record<string, unknown>;
};

export type SkillBindingView = {
  id: string;
  skillKey: string;
  isEnabled: boolean;
  displayName: string | null;
  sortOrder: number;
  configOverrides: Record<string, unknown>;
  toolOverrides: ToolBindingView[];
};

export type VersionDetailView = AgentVersionSummaryView & {
  systemPromptTemplate: string;
  defaultLocale: string | null;
  runtimeOptions: Record<string, unknown>;
  handoffPolicy: Record<string, unknown>;
  responsePolicy: Record<string, unknown>;
  guardrailsPolicy: AgentLocalGuardrailsPolicy;
  toolBindings: ToolBindingView[];
  knowledgeBaseBindings: KnowledgeBaseBindingView[];
  mcpBindings: McpBindingView[];
  skillBindings: SkillBindingView[];
};

export type ToolBindingWriteModel = {
  toolName: string;
  displayName: string | null;
  description: string | null;
  invocationMode: InvocationMode;
  isRequired: boolean;
  config: Record<string, unknown>;
  sortOrder: number;
  isEnabled: boolean;
};

export type CreateVersionRequest = {
  systemPromptTemplate: string;
  modelKey: string;
  versionLabel: string | null;
  changeSummary: string | null;
  defaultLocale: string | null;
  runtimeOptions: Record<string, unknown> | null;
  handoffPolicy: Record<string, unknown> | null;
  responsePolicy: Record<string, unknown> | null;
  guardrailsPolicy: AgentLocalGuardrailsPolicy | null;
  toolBindings: ToolBindingWriteModel[];
  knowledgeBaseBindings: VersionKnowledgeBaseBindingRequest[];
  mcpBindings: VersionMcpBindingRequest[];
  skillBindings: VersionSkillBindingRequest[];
};

export type UpdateVersionRequest = CreateVersionRequest & {
  rowVersion: number;
};

export type PublishAgentRequest = {
  versionNumber: number | null;
  definitionRowVersion: number | null;
  versionRowVersion: number | null;
};

export type DisableAgentRequest = {
  reason: string | null;
  rowVersion: number | null;
};

// ── Execution Audit ──

export type ExecutionAuditView = {
  id: string;
  agentKey: string;
  runId: string;
  agentVersion: number | null;
  inputSummary: string | null;
  outputSummary: string | null;
  toolCallsJson: unknown[];
  status: string;
  durationMs: number | null;
  tokenUsageJson: Record<string, unknown>;
  errorMessage: string | null;
  createdAtUtc: string | null;
};

export type AuditListQuery = {
  page: number;
  pageSize: number;
};

// Detail view uses the shared agent trace contract until the backend
// audit-detail endpoint is enhanced with richer trace data.
export type { AgentExecutionTrace as ExecutionAuditDetailView } from '@/shared/agent-trace/contracts';
