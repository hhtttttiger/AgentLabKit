import { apiRequest } from '@/shared/api/client';
import type { LlmModelBindingListQuery, LlmModelBindingView, LlmModelBindingWriteModel, LlmPagedResult } from '../../lib/contracts';

export function listModelBindings(query: LlmModelBindingListQuery) {
  return apiRequest<LlmPagedResult<LlmModelBindingView>>('/api/llm-catalog/model-bindings', { query });
}

export function createModelBinding(model: LlmModelBindingWriteModel) {
  return apiRequest<LlmModelBindingView>('/api/llm-catalog/model-bindings', { method: 'POST', body: model });
}

export function updateModelBinding(bindingKey: string, model: LlmModelBindingWriteModel) {
  return apiRequest<LlmModelBindingView>(`/api/llm-catalog/model-bindings/${bindingKey}`, { method: 'PUT', body: model });
}

export function deleteModelBinding(bindingKey: string) {
  return apiRequest<{ bindingKey: string; deleted: boolean }>(`/api/llm-catalog/model-bindings/${bindingKey}`, { method: 'DELETE' });
}
