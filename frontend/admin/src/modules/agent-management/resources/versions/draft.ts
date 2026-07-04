import type {
  AgentLocalGuardrailsPolicy,
  CreateVersionRequest,
  KnowledgeBaseBindingWriteModel,
  McpBindingWriteModel,
  SkillBindingWriteModel,
  ToolBindingWriteModel,
  VersionDetailView,
} from '../../lib/contracts';

export type VersionEditorDraft = {
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
  knowledgeBaseBindings: KnowledgeBaseBindingWriteModel[];
  mcpBindings: McpBindingWriteModel[];
  skillBindings: SkillBindingWriteModel[];
};

function hasNonEmptyObject(obj: Record<string, unknown> | null | undefined): boolean {
  return obj !== null && obj !== undefined && Object.keys(obj).length > 0;
}

export function createEmptyMcpBinding(): McpBindingWriteModel {
  return {
    serverName: '',
    toolWhitelist: null,
    isEnabled: true,
  };
}

export function createEmptySkillBinding(sortOrder: number): SkillBindingWriteModel {
  return {
    skillKey: '',
    configOverrides: {},
    toolOverrides: [],
    sortOrder,
    isEnabled: true,
  };
}

export function validateVersionDraft(draft: VersionEditorDraft) {
  const errors: Record<string, string> = {};

  if (!(draft.systemPromptTemplate ?? '').trim()) {
    errors.systemPromptTemplate = '请输入 System Prompt。';
  }

  if (!(draft.modelKey ?? '').trim()) {
    errors.modelKey = '请输入模型绑定标识。';
  }

  draft.toolBindings.forEach((binding, index) => {
    if (!(binding.toolName ?? '').trim()) {
      errors[`tool_${index}_toolName`] = `工具 #${index + 1} 名称不能为空。`;
      return;
    }

    const duplicateIndex = draft.toolBindings.findIndex(
      (item, itemIndex) => itemIndex !== index && (item.toolName ?? '').trim() === (binding.toolName ?? '').trim(),
    );
    if (duplicateIndex >= 0) {
      errors[`tool_${index}_toolName`] = `工具 #${index + 1} 与工具 #${duplicateIndex + 1} 名称重复。`;
    }
  });

  draft.mcpBindings.forEach((binding, index) => {
    if (!(binding.serverName ?? '').trim()) {
      errors[`mcp_${index}_serverName`] = `MCP 绑定 #${index + 1} 需要选择 MCP Server。`;
    }
  });

  draft.knowledgeBaseBindings.forEach((binding, index) => {
    if (!(binding.knowledgeBaseId ?? '').trim()) {
      errors[`kb_${index}_knowledgeBaseId`] = `知识库绑定 #${index + 1} 需要选择知识库。`;
      return;
    }

    const duplicateIndex = draft.knowledgeBaseBindings.findIndex(
      (item, itemIndex) => itemIndex !== index && (item.knowledgeBaseId ?? '').trim() === (binding.knowledgeBaseId ?? '').trim(),
    );
    if (duplicateIndex >= 0) {
      errors[`kb_${index}_knowledgeBaseId`] = `知识库绑定 #${index + 1} 与知识库绑定 #${duplicateIndex + 1} 选择重复。`;
    }
  });

  draft.skillBindings.forEach((binding, skillIndex) => {
    if (!(binding.skillKey ?? '').trim()) {
      errors[`skill_${skillIndex}_skillKey`] = `技能绑定 #${skillIndex + 1} 需要选择技能。`;
    }

    binding.toolOverrides.forEach((tool, toolIndex) => {
      if (!(tool.toolName ?? '').trim()) {
        errors[`skill_${skillIndex}_tool_${toolIndex}_toolName`] =
          `技能绑定 #${skillIndex + 1} 的工具覆盖 #${toolIndex + 1} 名称不能为空。`;
      }
    });
  });

  return errors;
}

export function policyToDisplay(obj: Record<string, unknown> | null): string {
  if (!obj || Object.keys(obj).length === 0) {
    return '';
  }

  return JSON.stringify(obj);
}

export function displayToPolicy(text: string): Record<string, unknown> | null {
  const trimmed = text.trim();
  if (!trimmed || trimmed === '{}') {
    return null;
  }

  return JSON.parse(trimmed) as Record<string, unknown>;
}

export function versionDetailToDraft(version: VersionDetailView): VersionEditorDraft {
  const systemPromptTemplate =
    version.systemPromptTemplate
    ?? (version as { systemPrompt?: unknown }).systemPrompt
    ?? '';

  return {
    systemPromptTemplate,
    modelKey: version.modelKey ?? '',
    versionLabel: version.versionLabel,
    changeSummary: version.changeSummary,
    defaultLocale: version.defaultLocale,
    runtimeOptions: version.runtimeOptions as Record<string, unknown> | null,
    handoffPolicy: version.handoffPolicy as Record<string, unknown> | null,
    responsePolicy: version.responsePolicy as Record<string, unknown> | null,
    guardrailsPolicy: version.guardrailsPolicy as AgentLocalGuardrailsPolicy | null,
    toolBindings: (version.toolBindings ?? []).map((binding) => ({
      ...binding,
      config: binding.config as Record<string, unknown>,
    })),
    knowledgeBaseBindings: (version.knowledgeBaseBindings ?? []).map((b) => ({
      id: b.id,
      knowledgeBaseId: b.knowledgeBaseId,
      sortOrder: b.sortOrder,
      isEnabled: b.isEnabled,
      config: b.config,
    })),
    mcpBindings: (version.mcpBindings ?? []).map((b) => ({
      serverName: b.serverName,
      toolWhitelist: b.toolWhitelist,
      isEnabled: b.isEnabled,
    })),
    skillBindings: (version.skillBindings ?? []).map((b) => ({
      skillKey: b.skillKey,
      configOverrides: b.configOverrides,
      toolOverrides: b.toolOverrides,
      sortOrder: b.sortOrder,
      isEnabled: b.isEnabled,
    })),
  };
}

export function ensureVersionDefaultPolicy(draft: VersionEditorDraft): CreateVersionRequest {
  const serializeToolBindings = (bindings: ToolBindingWriteModel[]) => bindings.map((binding) => ({
    toolName: binding.toolName,
    displayName: binding.displayName,
    description: binding.description,
    invocationMode: binding.invocationMode,
    isRequired: binding.isRequired,
    config: binding.config,
    sortOrder: binding.sortOrder,
    isEnabled: binding.isEnabled,
  }));

  const baseRequest: CreateVersionRequest = {
    systemPromptTemplate: draft.systemPromptTemplate,
    modelKey: draft.modelKey,
    versionLabel: draft.versionLabel,
    changeSummary: draft.changeSummary,
    defaultLocale: draft.defaultLocale,
    runtimeOptions: draft.runtimeOptions,
    handoffPolicy: draft.handoffPolicy,
    responsePolicy: draft.responsePolicy,
    guardrailsPolicy: draft.guardrailsPolicy,
    toolBindings: serializeToolBindings(draft.toolBindings),
    knowledgeBaseBindings: draft.knowledgeBaseBindings.map((binding) => ({
      knowledgeBaseId: binding.knowledgeBaseId,
      sortOrder: binding.sortOrder,
      isEnabled: binding.isEnabled,
      config: binding.config,
    })),
    mcpBindings: draft.mcpBindings.map((binding) => ({
      serverName: binding.serverName,
      isEnabled: binding.isEnabled,
      toolWhitelist: binding.toolWhitelist,
      configOverrides: {},
    })),
    skillBindings: draft.skillBindings.map((binding) => ({
      skillKey: binding.skillKey,
      isEnabled: binding.isEnabled,
      bindingOrder: binding.sortOrder,
      config: binding.configOverrides,
      toolOverrides: binding.toolOverrides.length > 0 ? serializeToolBindings(binding.toolOverrides) : null,
    })),
  };

  const hasPolicy =
    hasNonEmptyObject(draft.runtimeOptions) ||
    hasNonEmptyObject(draft.handoffPolicy) ||
    hasNonEmptyObject(draft.responsePolicy) ||
    hasNonEmptyObject(draft.guardrailsPolicy);

  if (hasPolicy) {
    return baseRequest;
  }

  return {
    ...baseRequest,
    responsePolicy: { mode: 'default' },
  };
}

export function emptyToolOverride(sortOrder: number): ToolBindingWriteModel {
  return {
    toolName: '',
    displayName: null,
    description: null,
    invocationMode: 'auto',
    isRequired: false,
    config: {},
    sortOrder,
    isEnabled: true,
  };
}
