import { apiRequest } from '@/shared/api/client';
import type { LlmConnectionProfileListQuery, LlmConnectionProfileView, LlmConnectionProfileWriteModel, LlmPagedResult } from '../../lib/contracts';

export function listConnectionProfiles(query: LlmConnectionProfileListQuery) {
  return apiRequest<LlmPagedResult<LlmConnectionProfileView>>('/api/llm-catalog/connection-profiles', { query });
}

export function createConnectionProfile(model: LlmConnectionProfileWriteModel) {
  return apiRequest<LlmConnectionProfileView>('/api/llm-catalog/connection-profiles', { method: 'POST', body: model });
}

export function updateConnectionProfile(profileKey: string, model: LlmConnectionProfileWriteModel) {
  return apiRequest<LlmConnectionProfileView>(`/api/llm-catalog/connection-profiles/${profileKey}`, { method: 'PUT', body: model });
}

export function deleteConnectionProfile(profileKey: string) {
  return apiRequest<{ profileKey: string; deleted: boolean }>(`/api/llm-catalog/connection-profiles/${profileKey}`, { method: 'DELETE' });
}
