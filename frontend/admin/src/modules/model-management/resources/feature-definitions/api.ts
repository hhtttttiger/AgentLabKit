import { apiRequest } from '@/shared/api/client';
import type {
  LlmFeatureListQuery,
  LlmFeatureView,
  LlmFeatureWriteModel,
  LlmPagedResult,
} from '../../lib/contracts';

export function listFeatures(query: LlmFeatureListQuery) {
  return apiRequest<LlmPagedResult<LlmFeatureView>>('/api/llm-catalog/features', { query });
}

export function getFeature(featureKey: string) {
  return apiRequest<LlmFeatureView>(`/api/llm-catalog/features/${featureKey}`);
}

export function createFeature(model: LlmFeatureWriteModel) {
  return apiRequest<LlmFeatureView>('/api/llm-catalog/features', { method: 'POST', body: model });
}

export function updateFeature(featureKey: string, model: LlmFeatureWriteModel) {
  return apiRequest<LlmFeatureView>(`/api/llm-catalog/features/${featureKey}`, { method: 'PUT', body: model });
}

export function deleteFeature(featureKey: string) {
  return apiRequest<{ featureKey: string; deleted: boolean }>(`/api/llm-catalog/features/${featureKey}`, { method: 'DELETE' });
}
