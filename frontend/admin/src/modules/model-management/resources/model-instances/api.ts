import { apiRequest } from '@/shared/api/client';
import type {
  LlmModelInstanceListQuery,
  LlmModelInstanceView,
  LlmModelInstanceWriteModel,
  LlmPagedResult,
} from '../../lib/contracts';

export function listModelInstances(query: LlmModelInstanceListQuery) {
  return apiRequest<LlmPagedResult<LlmModelInstanceView>>('/api/llm-catalog/model-instances', { query });
}

export function listModelInstancesByModel(modelKey: string) {
  return apiRequest<LlmPagedResult<LlmModelInstanceView>>(`/api/llm-catalog/models/${modelKey}/instances`);
}

export function createModelInstance(modelKey: string, model: LlmModelInstanceWriteModel) {
  return apiRequest<LlmModelInstanceView>(`/api/llm-catalog/models/${modelKey}/instances`, { method: 'POST', body: model });
}

export function updateModelInstance(instanceKey: string, model: LlmModelInstanceWriteModel) {
  return apiRequest<LlmModelInstanceView>(`/api/llm-catalog/model-instances/${instanceKey}`, { method: 'PUT', body: model });
}

export function deleteModelInstance(instanceKey: string) {
  return apiRequest<{ instanceKey: string; deleted: boolean }>(`/api/llm-catalog/model-instances/${instanceKey}`, { method: 'DELETE' });
}
