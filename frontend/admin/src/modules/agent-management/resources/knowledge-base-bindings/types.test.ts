import { describe, expect, it } from 'vitest';
import type { KbView } from '@/modules/knowledge-base/lib/contracts';
import type { ToolBindingView } from '../../lib/contracts';
import {
  buildKnowledgeBaseBindingCandidates,
  hasUsableKnowledgeSearchBinding,
  mergeKnowledgeBaseBindingRows,
  type VersionKnowledgeBaseBindingApiView,
} from './types';

const bindings: VersionKnowledgeBaseBindingApiView[] = [
  {
    id: 'binding-1',
    knowledgeBaseId: 'kb-1',
    sortOrder: 10,
    isEnabled: true,
    config: {},
    createdAtUtc: '2026-04-30T00:00:00Z',
    updatedAtUtc: null,
  },
];

const knowledgeBases: KbView[] = [
  {
    id: 'kb-1',
    name: 'Policies',
    description: 'Policy docs',
    sourceType: 'local',
    documentCount: 12,
    status: 'Active',
    createdAtUtc: '2026-04-20T00:00:00Z',
  },
  {
    id: 'kb-2',
    name: 'FAQ',
    description: 'FAQ docs',
    sourceType: 'local',
    documentCount: 3,
    status: 'Active',
    createdAtUtc: '2026-04-21T00:00:00Z',
  },
];

describe('knowledge base binding helpers', () => {
  it('joins binding rows with knowledge base catalog and falls back gracefully when catalog is missing', () => {
    expect(mergeKnowledgeBaseBindingRows(bindings, knowledgeBases)).toEqual([
      expect.objectContaining({
        id: 'binding-1',
        knowledgeBaseId: 'kb-1',
        knowledgeBaseName: 'Policies',
        knowledgeBaseStatus: 'Active',
      }),
    ]);

    expect(mergeKnowledgeBaseBindingRows(bindings, [])).toEqual([
      expect.objectContaining({
        knowledgeBaseName: '知识库 kb-1',
        knowledgeBaseStatus: null,
      }),
    ]);
  });

  it('filters already-bound knowledge bases out of the candidate list', () => {
    expect(buildKnowledgeBaseBindingCandidates(knowledgeBases, bindings)).toEqual([
      { value: 'kb-2', label: 'FAQ', status: 'Active' },
    ]);
  });

  it('treats enabled non-disabled knowledge_search bindings as runtime-usable', () => {
    const toolBindings: ToolBindingView[] = [
      {
        toolName: 'knowledge_search',
        displayName: 'Knowledge Search',
        description: null,
        invocationMode: 'auto',
        isRequired: false,
        config: {},
        sortOrder: 0,
        isEnabled: true,
      },
    ];

    expect(hasUsableKnowledgeSearchBinding(toolBindings)).toBe(true);
    expect(hasUsableKnowledgeSearchBinding([{ ...toolBindings[0], isEnabled: false }])).toBe(false);
    expect(hasUsableKnowledgeSearchBinding([{ ...toolBindings[0], invocationMode: 'disabled' }])).toBe(false);
  });
});
