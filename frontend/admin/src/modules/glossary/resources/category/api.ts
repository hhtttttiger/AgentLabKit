import { apiRequest } from '@/shared/api/client';
import type {
  GlossaryCategoryCreateRequest,
  GlossaryCategoryPage,
  GlossaryCategoryUpdateRequest,
  GlossaryCategoryView,
  GlossaryCategoryListQuery,
} from '../../lib/contracts';

export function listGlossaryCategories(query: GlossaryCategoryListQuery = {}) {
  return apiRequest<GlossaryCategoryPage>('/api/glossary/categories', { query });
}

export function getGlossaryCategory(categoryId: string) {
  return apiRequest<GlossaryCategoryView>(`/api/glossary/categories/${categoryId}`);
}

export function createGlossaryCategory(data: GlossaryCategoryCreateRequest) {
  return apiRequest<GlossaryCategoryView>('/api/glossary/categories', { method: 'POST', body: data });
}

export function updateGlossaryCategory(categoryId: string, data: GlossaryCategoryUpdateRequest) {
  return apiRequest<GlossaryCategoryView>(`/api/glossary/categories/${categoryId}`, {
    method: 'PUT',
    body: data,
  });
}

export function deleteGlossaryCategory(categoryId: string) {
  return apiRequest<void>(`/api/glossary/categories/${categoryId}`, { method: 'DELETE' });
}
