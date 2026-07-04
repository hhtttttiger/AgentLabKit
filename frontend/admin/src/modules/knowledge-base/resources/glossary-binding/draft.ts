import type { GlossaryCategoryView } from '@/modules/glossary/lib/contracts';

export type GlossaryBindingDraft = { serverIds: string[]; draftIds: string[] };
export type GlossaryBindingDiff = { addedIds: string[]; removedIds: string[]; isDirty: boolean };
export type GlossaryBindingPanels = {
  available: GlossaryCategoryView[];
  bound: GlossaryCategoryView[];
};

function sortCategories(categories: GlossaryCategoryView[]) {
  return [...categories].sort((left, right) => left.name.localeCompare(right.name, 'zh-CN'));
}

function normalizeDraftIds(draftIds: string[], categories: GlossaryCategoryView[]) {
  const knownIds = new Set(categories.map((item) => item.id));
  const orderedIds = sortCategories(categories).map((item) => item.id);
  const draftSet = new Set(draftIds.filter((id) => knownIds.has(id)));
  return orderedIds.filter((id) => draftSet.has(id));
}

function matchesQuery(category: GlossaryCategoryView, query: string) {
  const keyword = query.trim().toLowerCase();
  if (!keyword) {
    return true;
  }

  return (
    category.name.toLowerCase().includes(keyword) ||
    (category.description ?? '').toLowerCase().includes(keyword)
  );
}

export function createGlossaryBindingDraft(binding: {
  categoryIds: string[];
  categories: GlossaryCategoryView[];
}): GlossaryBindingDraft {
  return {
    serverIds: normalizeDraftIds(binding.categoryIds, binding.categories),
    draftIds: normalizeDraftIds(binding.categoryIds, binding.categories),
  };
}

export function addGlossaryCategoryToDraft(
  draftIds: string[],
  categoryId: string,
  categories: GlossaryCategoryView[],
): string[] {
  return normalizeDraftIds([...draftIds, categoryId], categories);
}

export function removeGlossaryCategoryFromDraft(
  draftIds: string[],
  categoryId: string,
  categories: GlossaryCategoryView[],
): string[] {
  return normalizeDraftIds(draftIds.filter((id) => id !== categoryId), categories);
}

export function getGlossaryBindingPanels(
  draftIds: string[],
  categories: GlossaryCategoryView[],
  query: string,
): GlossaryBindingPanels {
  const ordered = sortCategories(categories);
  const draftSet = new Set(draftIds);

  return {
    available: ordered.filter((item) => !draftSet.has(item.id) && matchesQuery(item, query)),
    bound: ordered.filter((item) => draftSet.has(item.id)),
  };
}

export function summarizeGlossaryBindingDraft(serverIds: string[], draftIds: string[]): GlossaryBindingDiff {
  const serverSet = new Set(serverIds);
  const draftSet = new Set(draftIds);
  const addedIds = draftIds.filter((id) => !serverSet.has(id));
  const removedIds = serverIds.filter((id) => !draftSet.has(id));

  return {
    addedIds,
    removedIds,
    isDirty: addedIds.length > 0 || removedIds.length > 0,
  };
}
