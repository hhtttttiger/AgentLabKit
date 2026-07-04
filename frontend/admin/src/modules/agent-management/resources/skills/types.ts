import type { ToolBindingWriteModel } from '../../lib/contracts';
import type { SkillFlowDocument } from './workbench/lib/types';

export type SkillStatus = 'draft' | 'published';

export type PromptSection = {
  key: string;
  content: string;
  sortOrder: number;
};

export type SkillDefinitionApiView = {
  id: string;
  skillKey: string;
  displayName: string;
  description: string;
  version: string;
  spec: Record<string, unknown>;
  isPublished: boolean;
  createdAtUtc: string;
  updatedAtUtc: string | null;
};

export type SkillSummaryView = {
  id: string;
  skillKey: string;
  displayName: string;
  description: string;
  version: string;
  status: SkillStatus;
  tags: string[];
  promptSections: PromptSection[];
  toolBindings: ToolBindingWriteModel[];
  configSchema: Record<string, unknown>;
  spec: Record<string, unknown>;
  orchestration: SkillFlowDocument | null;
  createdAtUtc: string;
  updatedAtUtc: string | null;
};

export type SkillDetailView = SkillSummaryView;

export type SkillListQuery = {
  publishedOnly?: boolean;
};

export type CreateSkillRequest = {
  skillKey: string;
  displayName: string;
  description: string;
  version: string;
  tags: string[];
  promptSections: PromptSection[];
  toolBindings: ToolBindingWriteModel[];
  configSchema: Record<string, unknown>;
  spec: Record<string, unknown>;
  orchestration: SkillFlowDocument | null;
};

export type UpdateSkillRequest = Omit<CreateSkillRequest, 'skillKey'>;

export type CreateSkillDefinitionApiRequest = {
  skillKey: string;
  displayName: string;
  description: string;
  version: string;
  spec: Record<string, unknown>;
};

export type UpdateSkillDefinitionApiRequest = {
  displayName: string;
  description: string;
  version: string;
  spec: Record<string, unknown>;
};

export type SkillBindingApiView = {
  id: string;
  skillKey: string;
  isEnabled: boolean;
  bindingOrder: number;
  config: Record<string, unknown>;
  toolOverrides: Record<string, unknown>[] | null;
  createdAtUtc: string;
  updatedAtUtc: string | null;
};

export type SkillBindingApiRequest = {
  skillKey: string;
  isEnabled: boolean;
  bindingOrder: number;
  config: Record<string, unknown>;
  toolOverrides: Record<string, unknown>[] | null;
};

export type SkillFilters = {
  status: '' | SkillStatus;
  tag: string;
  search: string;
  page: number;
  pageSize: number;
};

export const defaultSkillFilters: SkillFilters = {
  status: '',
  tag: '',
  search: '',
  page: 1,
  pageSize: 20,
};

function asStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
    : [];
}

function asPromptSections(value: unknown): PromptSection[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.flatMap((item, index) => {
    if (!item || typeof item !== 'object') return [];
    const record = item as Record<string, unknown>;
    return [{
      key: typeof record.key === 'string' ? record.key : `section_${index}`,
      content: typeof record.content === 'string' ? record.content : '',
      sortOrder: typeof record.sortOrder === 'number' ? record.sortOrder : index,
    }];
  });
}

function asToolBindings(value: unknown): ToolBindingWriteModel[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item, index) => {
    if (!item || typeof item !== 'object') return [];
    const record = item as Record<string, unknown>;
    return [{
      toolName: typeof record.toolName === 'string' ? record.toolName : '',
      displayName: typeof record.displayName === 'string' ? record.displayName : null,
      description: typeof record.description === 'string' ? record.description : null,
      invocationMode:
        record.invocationMode === 'manual_only' || record.invocationMode === 'disabled'
          ? record.invocationMode
          : 'auto',
      isRequired: record.isRequired === true,
      config: record.config && typeof record.config === 'object' ? record.config as Record<string, unknown> : {},
      sortOrder: typeof record.sortOrder === 'number' ? record.sortOrder : index,
      isEnabled: record.isEnabled !== false,
    }];
  });
}

function asObjectRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? { ...(value as Record<string, unknown>) }
    : {};
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value);
}

function isInputField(value: unknown): boolean {
  return isRecord(value) && typeof value.key === 'string' && typeof value.label === 'string';
}

function isInputFieldArray(value: unknown): boolean {
  return Array.isArray(value) && value.every(isInputField);
}

function isOutputFieldArray(value: unknown): boolean {
  return Array.isArray(value) && value.every(isInputField);
}

function isToolInvocationPlanArray(value: unknown): boolean {
  return Array.isArray(value) && value.every((item) =>
    isRecord(item)
    && typeof item.id === 'string'
    && typeof item.toolId === 'string'
    && typeof item.reason === 'string');
}

function isFallbackPolicy(value: unknown): boolean {
  if (!isRecord(value) || typeof value.mode !== 'string' || typeof value.note !== 'string') {
    return false;
  }

  if (value.mode === 'stay' || value.mode === 'handoff') {
    return true;
  }

  return value.mode === 'goto' && typeof value.transitionId === 'string';
}

function isPredicateExpression(value: unknown): boolean {
  if (!isRecord(value) || typeof value.field !== 'string' || typeof value.operator !== 'string') {
    return false;
  }

  if (value.operator === 'eq') {
    return typeof value.value === 'string';
  }

  return value.operator === 'in'
    && Array.isArray(value.value)
    && value.value.every((item) => typeof item === 'string');
}

function isPredicate(value: unknown): boolean {
  return isRecord(value)
    && typeof value.description === 'string'
    && isPredicateExpression(value.expression);
}

function isSkillFlowState(value: unknown): boolean {
  if (!isRecord(value) || typeof value.id !== 'string' || typeof value.kind !== 'string' || typeof value.title !== 'string') {
    return false;
  }

  switch (value.kind) {
    case 'start':
      return true;
    case 'task':
      return typeof value.goal === 'string'
        && isToolInvocationPlanArray(value.toolPlan)
        && isRecord(value.inputContract)
        && isInputFieldArray(value.inputContract.inherited)
        && isInputFieldArray(value.inputContract.required)
        && isInputFieldArray(value.inputContract.optional)
        && isOutputFieldArray(value.outputContract)
        && isFallbackPolicy(value.fallbackPolicy);
    case 'decision':
      return typeof value.question === 'string';
    case 'handoff':
      return typeof value.handoffType === 'string'
        && (value.handoffType === 'human' || value.handoffType === 'ticket' || value.handoffType === 'other_agent')
        && typeof value.summaryTemplate === 'string';
    case 'terminal':
      return typeof value.outcome === 'string'
        && (value.outcome === 'resolved' || value.outcome === 'blocked' || value.outcome === 'cancelled')
        && typeof value.resolutionNote === 'string';
    default:
      return false;
  }
}

function isSkillFlowTransition(value: unknown): boolean {
  return isRecord(value)
    && typeof value.id === 'string'
    && typeof value.fromStateId === 'string'
    && typeof value.toStateId === 'string'
    && typeof value.label === 'string'
    && typeof value.kind === 'string'
    && ['default', 'condition', 'fallback', 'error', 'handoff'].includes(value.kind)
    && typeof value.priority === 'number'
    && Number.isFinite(value.priority)
    && (value.predicate === undefined || isPredicate(value.predicate));
}

function isSkillFlowStateMap(value: unknown): boolean {
  return isRecord(value) && Object.values(value).every(isSkillFlowState);
}

function isSkillFlowTransitionMap(value: unknown): boolean {
  return isRecord(value) && Object.values(value).every(isSkillFlowTransition);
}

function asSkillFlowDocument(value: unknown): SkillFlowDocument | null {
  if (!isRecord(value)) {
    return null;
  }

  const record = value;
  const metadata = record.metadata;
  const states = record.states;
  const transitions = record.transitions;

  if (
    record.version !== '3'
    || typeof record.entryStateId !== 'string'
    || !isRecord(metadata)
    || !isSkillFlowStateMap(states)
    || !isSkillFlowTransitionMap(transitions)
  ) {
    return null;
  }

  if (
    typeof metadata.skillKey !== 'string'
    || typeof metadata.displayName !== 'string'
    || typeof metadata.description !== 'string'
    || typeof metadata.version !== 'string'
  ) {
    return null;
  }

  return {
    version: '3',
    entryStateId: record.entryStateId,
    metadata: {
      skillKey: metadata.skillKey,
      displayName: metadata.displayName,
      description: metadata.description,
      version: metadata.version,
    },
    states: states as SkillFlowDocument['states'],
    transitions: transitions as SkillFlowDocument['transitions'],
  };
}

export function mapSkillDefinition(api: SkillDefinitionApiView): SkillSummaryView {
  const spec = asObjectRecord(api.spec);

  return {
    id: api.id,
    skillKey: api.skillKey,
    displayName: api.displayName,
    description: api.description ?? '',
    version: api.version,
    status: api.isPublished ? 'published' : 'draft',
    tags: asStringArray(spec.tags),
    promptSections: asPromptSections(spec.promptSections),
    toolBindings: asToolBindings(spec.toolBindings),
    configSchema: asObjectRecord(spec.configSchema),
    spec,
    orchestration: asSkillFlowDocument(spec.orchestration),
    createdAtUtc: api.createdAtUtc,
    updatedAtUtc: api.updatedAtUtc,
  };
}

export function toSkillListQuery(filters: SkillFilters): SkillListQuery {
  return {
    ...(filters.status === 'published' ? { publishedOnly: true } : {}),
  };
}

export function filterSkillRows(rows: SkillSummaryView[], filters: SkillFilters) {
  const search = (filters.search ?? '').trim().toLowerCase();
  const tag = (filters.tag ?? '').trim().toLowerCase();

  return rows.filter((row) => {
    if (filters.status && row.status !== filters.status) return false;
    if (tag && !row.tags.some((item) => item.toLowerCase().includes(tag))) return false;
    if (!search) return true;

    return [row.skillKey, row.displayName, row.description, row.version, ...row.tags]
      .some((value) => value.toLowerCase().includes(search));
  });
}

export function paginateRows<T>(rows: T[], page: number, pageSize: number) {
  const start = (page - 1) * pageSize;
  return rows.slice(start, start + pageSize);
}

function mergeSkillSpec(draft: Pick<CreateSkillRequest, 'tags' | 'promptSections' | 'toolBindings' | 'configSchema' | 'spec' | 'orchestration'>) {
  return {
    ...draft.spec,
    tags: draft.tags,
    promptSections: draft.promptSections,
    toolBindings: draft.toolBindings,
    configSchema: draft.configSchema,
    ...(draft.orchestration ? { orchestration: draft.orchestration } : {}),
  };
}

export function toSkillDefinitionApiCreateRequest(draft: CreateSkillRequest): CreateSkillDefinitionApiRequest {
  return {
    skillKey: (draft.skillKey ?? '').trim(),
    displayName: (draft.displayName ?? '').trim(),
    description: (draft.description ?? '').trim(),
    version: (draft.version ?? '').trim(),
    spec: mergeSkillSpec(draft),
  };
}

export function toSkillDefinitionApiUpdateRequest(draft: UpdateSkillRequest): UpdateSkillDefinitionApiRequest {
  return {
    displayName: (draft.displayName ?? '').trim(),
    description: (draft.description ?? '').trim(),
    version: (draft.version ?? '').trim(),
    spec: mergeSkillSpec(draft),
  };
}

export const emptySkillDraft: CreateSkillRequest = {
  skillKey: '',
  displayName: '',
  description: '',
  version: '1.0.0',
  tags: [],
  promptSections: [],
  toolBindings: [],
  configSchema: {},
  spec: {},
  orchestration: null,
};
