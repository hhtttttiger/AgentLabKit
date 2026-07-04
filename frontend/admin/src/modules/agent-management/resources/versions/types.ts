import type { InvocationMode, ToolBindingWriteModel } from '../../lib/contracts';
import type { VersionEditorDraft } from './draft';

export const emptyToolBinding: ToolBindingWriteModel = {
  toolName: '',
  displayName: null,
  description: null,
  invocationMode: 'auto' as InvocationMode,
  isRequired: false,
  config: {},
  sortOrder: 0,
  isEnabled: true,
};

export const emptyVersionDraft: VersionEditorDraft = {
  systemPromptTemplate: '',
  modelKey: '',
  versionLabel: null,
  changeSummary: null,
  defaultLocale: null,
  runtimeOptions: null,
  handoffPolicy: null,
  responsePolicy: { mode: 'default' },
  guardrailsPolicy: null,
  toolBindings: [],
  knowledgeBaseBindings: [],
  mcpBindings: [],
  skillBindings: [],
};
