import type { KbStatus, KbView } from '@/modules/knowledge-base/lib/contracts';
import type { ToolBindingView } from '../../lib/contracts';

export type VersionKnowledgeBaseBindingApiView = {
  id: string;
  knowledgeBaseId: string;
  sortOrder: number;
  isEnabled: boolean;
  config: Record<string, unknown>;
  createdAtUtc: string;
  updatedAtUtc: string | null;
};

export type CreateVersionKnowledgeBaseBindingRequest = {
  knowledgeBaseId: string;
  sortOrder: number;
  isEnabled: boolean;
  config: Record<string, unknown>;
};

export type UpdateVersionKnowledgeBaseBindingRequest = {
  sortOrder: number;
  isEnabled: boolean;
  config: Record<string, unknown>;
};

export type KnowledgeBaseBindingCandidate = {
  value: string;
  label: string;
  status: KbStatus;
};

export type VersionKnowledgeBaseBindingRowView = VersionKnowledgeBaseBindingApiView & {
  knowledgeBaseName: string;
  knowledgeBaseStatus: KbStatus | null;
};

export function mergeKnowledgeBaseBindingRows(
  bindings: VersionKnowledgeBaseBindingApiView[],
  knowledgeBases: KbView[],
): VersionKnowledgeBaseBindingRowView[] {
  const kbById = new Map(knowledgeBases.map((kb) => [kb.id, kb]));

  return bindings.map((binding) => {
    const kb = kbById.get(binding.knowledgeBaseId);

    return {
      ...binding,
      knowledgeBaseName: kb?.name ?? `知识库 ${binding.knowledgeBaseId}`,
      knowledgeBaseStatus: kb?.status ?? null,
    };
  });
}

export function buildKnowledgeBaseBindingCandidates(
  knowledgeBases: KbView[],
  bindings: VersionKnowledgeBaseBindingApiView[],
): KnowledgeBaseBindingCandidate[] {
  const existing = new Set(bindings.map((binding) => binding.knowledgeBaseId));

  return knowledgeBases
    .filter((kb) => !existing.has(kb.id))
    .map((kb) => ({
      value: kb.id,
      label: kb.name,
      status: kb.status,
    }));
}

export function hasUsableKnowledgeSearchBinding(toolBindings: ToolBindingView[]): boolean {
  return toolBindings.some((binding) =>
    binding.toolName === 'knowledge_search'
    && binding.isEnabled
    && binding.invocationMode !== 'disabled');
}
