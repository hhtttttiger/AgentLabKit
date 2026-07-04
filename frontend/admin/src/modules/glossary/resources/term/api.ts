import { apiRequest } from '@/shared/api/client';
import type {
  GlossaryImportResult,
  GlossaryTermCreateRequest,
  GlossaryTermListQuery,
  GlossaryTermPage,
  GlossaryTermUpdateRequest,
  GlossaryTermView,
} from '../../lib/contracts';

export function listGlossaryTerms(query: GlossaryTermListQuery = {}) {
  return apiRequest<GlossaryTermPage>('/api/glossary/terms', { query });
}

export function getGlossaryTerm(termId: string) {
  return apiRequest<GlossaryTermView>(`/api/glossary/terms/${termId}`);
}

export function createGlossaryTerm(data: GlossaryTermCreateRequest) {
  return apiRequest<GlossaryTermView>('/api/glossary/terms', { method: 'POST', body: data });
}

export function updateGlossaryTerm(termId: string, data: GlossaryTermUpdateRequest) {
  return apiRequest<GlossaryTermView>(`/api/glossary/terms/${termId}`, {
    method: 'PUT',
    body: data,
  });
}

export function deleteGlossaryTerm(termId: string) {
  return apiRequest<void>(`/api/glossary/terms/${termId}`, { method: 'DELETE' });
}

export function importGlossaryTerms(file: File) {
  const form = new FormData();
  form.append('file', file);

  return apiRequest<GlossaryImportResult>('/api/glossary/terms/import', {
    method: 'POST',
    formBody: form,
  });
}
