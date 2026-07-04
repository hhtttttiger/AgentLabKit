import type { LlmModelListQuery, LlmModelWriteModel } from '../../lib/contracts';
import { asOptionalBooleanFilter, asOptionalString } from '../../lib/forms';

export type ModelFilters = {
  featureKey: string;
  featureIsSupported: 'all' | 'true' | 'false';
  featureValueJson: string;
  isEnabled: 'all' | 'true' | 'false';
  page: number;
  pageSize: number;
};

export const defaultModelFilters: ModelFilters = {
  featureKey: '',
  featureIsSupported: 'all',
  featureValueJson: '',
  isEnabled: 'all',
  page: 1,
  pageSize: 10,
};

export const emptyModelDraft: LlmModelWriteModel = {
  modelKey: '',
  type: 'Text',
  modelName: '',
  displayName: '',
  description: null,
  connectionProfileKey: '',
  tagsJson: [],
  routingPolicyJson: {},
  retryPolicyJson: {},
  isEnabled: true,
};

export function toModelQuery(filters: ModelFilters): LlmModelListQuery {
  return {
    featureKey: filters.featureKey.trim() || undefined,
    featureIsSupported: asOptionalBooleanFilter(filters.featureIsSupported),
    featureValueJson: filters.featureValueJson.trim() || undefined,
    isEnabled: filters.isEnabled === 'all' ? undefined : filters.isEnabled === 'true',
    page: filters.page,
    pageSize: filters.pageSize,
  };
}

export function toModelDraft(draft: LlmModelWriteModel): LlmModelWriteModel {
  return {
    ...draft,
    description: asOptionalString(draft.description ?? ''),
  };
}
