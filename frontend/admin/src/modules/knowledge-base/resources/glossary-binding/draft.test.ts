import { describe, expect, it } from 'vitest';
import type { GlossaryCategoryView } from '@/modules/glossary/lib/contracts';
import type { KbGlossaryBindingView } from './api';
import {
  createGlossaryBindingDraft,
  getGlossaryBindingPanels,
  summarizeGlossaryBindingDraft,
  addGlossaryCategoryToDraft,
  removeGlossaryCategoryFromDraft,
} from './draft';

const categories: GlossaryCategoryView[] = [
  { id: 'cat-2', name: 'Agent', description: 'Agent prompt terms', createdAtUtc: '2026-04-27T00:00:00Z', updatedAtUtc: null },
  { id: 'cat-1', name: 'RAG', description: 'Retrieval terms', createdAtUtc: '2026-04-27T00:00:00Z', updatedAtUtc: null },
  { id: 'cat-3', name: 'Voice', description: 'Voice pipeline terms', createdAtUtc: '2026-04-27T00:00:00Z', updatedAtUtc: null },
];

const binding: KbGlossaryBindingView = {
  knowledgeBaseId: 'kb-1',
  categoryIds: ['cat-1'],
  categories,
};

describe('glossary binding draft helpers', () => {
  it('splits categories into available and bound buckets using stable category order', () => {
    const draft = createGlossaryBindingDraft(binding);
    const panels = getGlossaryBindingPanels(draft.draftIds, binding.categories, '');

    expect(panels.available.map((item) => item.id)).toEqual(['cat-2', 'cat-3']);
    expect(panels.bound.map((item) => item.id)).toEqual(['cat-1']);
  });

  it('filters only the available panel when search is applied', () => {
    const draft = createGlossaryBindingDraft(binding);
    const panels = getGlossaryBindingPanels(draft.draftIds, binding.categories, 'voice');

    expect(panels.available.map((item) => item.id)).toEqual(['cat-3']);
    expect(panels.bound.map((item) => item.id)).toEqual(['cat-1']);
  });

  it('tracks added and removed ids relative to the server snapshot', () => {
    const added = addGlossaryCategoryToDraft(binding.categoryIds, 'cat-3', binding.categories);
    const removed = removeGlossaryCategoryFromDraft(added, 'cat-1', binding.categories);
    const summary = summarizeGlossaryBindingDraft(binding.categoryIds, removed);

    expect(summary.addedIds).toEqual(['cat-3']);
    expect(summary.removedIds).toEqual(['cat-1']);
    expect(summary.isDirty).toBe(true);
  });

  it('keeps ids normalized to known category order when items move in and out', () => {
    const withAgent = addGlossaryCategoryToDraft(binding.categoryIds, 'cat-2', binding.categories);
    const backToOriginal = removeGlossaryCategoryFromDraft(withAgent, 'cat-2', binding.categories);

    expect(withAgent).toEqual(['cat-2', 'cat-1']);
    expect(backToOriginal).toEqual(['cat-1']);
  });
});
