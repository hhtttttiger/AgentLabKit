import { apiRequest } from '@/shared/api/client';
import type { LlmModelFeatureView, LlmModelFeatureWriteModel, LlmModelListQuery, LlmModelView, LlmModelWriteModel, LlmPagedResult } from '../../lib/contracts';

export function listModels(query: LlmModelListQuery) {
  return apiRequest<LlmPagedResult<LlmModelView>>('/api/llm-catalog/models', { query });
}

export function getModel(modelKey: string) {
  return apiRequest<LlmModelView>(`/api/llm-catalog/models/${modelKey}`);
}

export function createModel(model: LlmModelWriteModel) {
  return apiRequest<LlmModelView>('/api/llm-catalog/models', { method: 'POST', body: model });
}

export function updateModel(modelKey: string, model: LlmModelWriteModel) {
  return apiRequest<LlmModelView>(`/api/llm-catalog/models/${modelKey}`, { method: 'PUT', body: model });
}

export function deleteModel(modelKey: string) {
  return apiRequest<{ modelKey: string; deleted: boolean }>(`/api/llm-catalog/models/${modelKey}`, { method: 'DELETE' });
}

export function upsertModelFeature(modelKey: string, featureKey: string, model: LlmModelFeatureWriteModel) {
  return apiRequest<LlmModelFeatureView>(`/api/llm-catalog/models/${modelKey}/features/${featureKey}`, { method: 'PUT', body: model });
}

export function deleteModelFeature(modelKey: string, featureKey: string) {
  return apiRequest<{ modelKey: string; featureKey: string; deleted: boolean }>(`/api/llm-catalog/models/${modelKey}/features/${featureKey}`, { method: 'DELETE' });
}
