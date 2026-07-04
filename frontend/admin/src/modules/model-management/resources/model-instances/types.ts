import type { CardCapability, LlmModelInstanceListQuery, LlmModelInstanceWriteModel } from '../../lib/contracts';
import { asOptionalBooleanFilter, asOptionalString } from '../../lib/forms';

export type ModelInstanceFilters = {
  modelKey: string;
  featureKey: string;
  featureIsSupported: 'all' | 'true' | 'false';
  featureValueJson: string;
  type: '' | CardCapability;
  isEnabled: 'all' | 'true' | 'false';
  isHealthy: 'all' | 'true' | 'false';
  page: number;
  pageSize: number;
};

export const defaultModelInstanceFilters: ModelInstanceFilters = {
  modelKey: '',
  featureKey: '',
  featureIsSupported: 'all',
  featureValueJson: '',
  type: '',
  isEnabled: 'all',
  isHealthy: 'all',
  page: 1,
  pageSize: 10,
};

export const emptyModelInstanceDraft: LlmModelInstanceWriteModel = {
  instanceKey: '',
  providerDeploymentName: null,
  region: null,
  priority: 1,
  weight: 100,
  defaultTimeoutMs: 30000,
  extraJson: {},
  isEnabled: true,
  isHealthy: true,
  apiKey: null,
};

export function toModelInstanceQuery(filters: ModelInstanceFilters): LlmModelInstanceListQuery {
  return {
    modelKey: filters.modelKey.trim() || undefined,
    featureKey: filters.featureKey.trim() || undefined,
    featureIsSupported: asOptionalBooleanFilter(filters.featureIsSupported),
    featureValueJson: filters.featureValueJson.trim() || undefined,
    type: filters.type || undefined,
    isEnabled: filters.isEnabled === 'all' ? undefined : filters.isEnabled === 'true',
    isHealthy: filters.isHealthy === 'all' ? undefined : filters.isHealthy === 'true',
    page: filters.page,
    pageSize: filters.pageSize,
  };
}

export function toModelInstanceDraft(draft: LlmModelInstanceWriteModel): LlmModelInstanceWriteModel {
  return {
    ...draft,
    providerDeploymentName: asOptionalString(draft.providerDeploymentName ?? ''),
    region: asOptionalString(draft.region ?? ''),
  };
}
