import { apiRequest } from '@/shared/api/client';
import type { KbCreateRequest, KbUpdateRequest, KbView, KbPagedResult } from '../../lib/contracts';

export function listKnowledgeBases(query: { page?: number; pageSize?: number; status?: string; keyword?: string }) {
  return apiRequest<KbPagedResult<KbView>>('/api/knowledge-bases', { query });
}

export function getKnowledgeBase(kbId: string) {
  return apiRequest<KbView>(`/api/knowledge-bases/${kbId}`);
}

export function createKnowledgeBase(data: KbCreateRequest) {
  return apiRequest<KbView>('/api/knowledge-bases', { method: 'POST', body: data });
}

export function updateKnowledgeBase(kbId: string, data: KbUpdateRequest) {
  return apiRequest<KbView>(`/api/knowledge-bases/${kbId}`, { method: 'PUT', body: data });
}

export function deleteKnowledgeBase(kbId: string) {
  return apiRequest<void>(`/api/knowledge-bases/${kbId}`, { method: 'DELETE' });
}
