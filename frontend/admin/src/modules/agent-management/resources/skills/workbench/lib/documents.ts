import type { ToolBindingWriteModel } from '../../../../lib/contracts';
import type { SkillSummaryView } from '../../types';
import type {
  SkillFlowDocument,
  SkillFlowMetadata,
  SkillWorkbenchTool,
} from './types';

type SkillMetadataSource = Pick<SkillSummaryView, 'skillKey' | 'displayName' | 'description' | 'version'>;

export function buildSkillFlowMetadata(source: SkillMetadataSource): SkillFlowMetadata {
  return {
    skillKey: source.skillKey,
    displayName: source.displayName,
    description: source.description,
    version: source.version,
  };
}

export function syncSkillFlowMetadata(
  document: SkillFlowDocument,
  source: SkillMetadataSource,
): SkillFlowDocument {
  return {
    ...document,
    metadata: buildSkillFlowMetadata(source),
  };
}

export function createDefaultSkillFlowDocument(source: SkillMetadataSource): SkillFlowDocument {
  return {
    version: '3',
    metadata: buildSkillFlowMetadata(source),
    entryStateId: 'start',
    states: {
      start: { id: 'start', kind: 'start', title: '开始' },
      analyze: {
        id: 'analyze',
        kind: 'task',
        title: '分析请求',
        goal: source.description || `处理技能「${source.displayName}」的请求。`,
        toolPlan: [],
        inputContract: {
          inherited: [],
          required: [],
          optional: [],
        },
        outputContract: [],
        fallbackPolicy: {
          mode: 'stay',
          note: '先补充缺失信息，再继续当前步骤。',
        },
      },
      done: {
        id: 'done',
        kind: 'terminal',
        title: '完成',
        outcome: 'resolved',
        resolutionNote: '流程已完成。',
      },
    },
    transitions: {
      'start-analyze': {
        id: 'start-analyze',
        fromStateId: 'start',
        toStateId: 'analyze',
        label: '开始',
        kind: 'default',
        priority: 0,
      },
      'analyze-done': {
        id: 'analyze-done',
        fromStateId: 'analyze',
        toStateId: 'done',
        label: '完成',
        kind: 'default',
        priority: 0,
      },
    },
  };
}

function getStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
    : [];
}

export function buildWorkbenchToolLibrary(bindings: ToolBindingWriteModel[]): SkillWorkbenchTool[] {
  return bindings
    .filter((binding) => (binding.toolName ?? '').trim().length > 0)
    .filter((binding) => binding.isEnabled !== false)
    .filter((binding) => binding.invocationMode !== 'disabled')
    .map((binding) => ({
      id: binding.toolName,
      name: binding.displayName?.trim() || binding.toolName,
      description: binding.description ?? null,
      isEnabled: binding.isEnabled !== false,
      isRequired: binding.isRequired,
      config: binding.config,
    }));
}

export function deriveToolInputs(binding: ToolBindingWriteModel): string[] {
  return getStringArray((binding.config as Record<string, unknown>).requiredInputs);
}
