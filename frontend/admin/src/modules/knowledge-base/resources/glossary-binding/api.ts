import type { GlossaryCategoryView } from '@/modules/glossary/lib/contracts';
import { apiRequest } from '@/shared/api/client';

export type KbGlossaryBindingView = {
  knowledgeBaseId: string;
  categoryIds: string[];
  categories: GlossaryCategoryView[];
};

export type ReplaceKbGlossaryBindingRequest = {
  kbId: string;
  categoryIds: string[];
};

export function getKnowledgeBaseGlossaryBinding(kbId: string): Promise<KbGlossaryBindingView> {
  return apiRequest<KbGlossaryBindingView>(`/api/knowledge-bases/${kbId}/glossary/categories`);
}

export function replaceKnowledgeBaseGlossaryBinding({ kbId, categoryIds }: ReplaceKbGlossaryBindingRequest) {
  return apiRequest<void>(`/api/knowledge-bases/${kbId}/glossary/categories`, {
    method: 'PUT',
    body: { categoryIds },
  });
}
