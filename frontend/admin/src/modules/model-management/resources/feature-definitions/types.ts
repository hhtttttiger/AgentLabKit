import type { LlmFeatureListQuery, LlmFeatureWriteModel } from '../../lib/contracts';
import { asOptionalString } from '../../lib/forms';

export type FeatureFilters = {
  valueType: '' | string;
  isEnabled: 'all' | 'true' | 'false';
  isFilterable: 'all' | 'true' | 'false';
  isRoutable: 'all' | 'true' | 'false';
  page: number;
  pageSize: number;
};

export const defaultFeatureFilters: FeatureFilters = {
  valueType: '',
  isEnabled: 'all',
  isFilterable: 'all',
  isRoutable: 'all',
  page: 1,
  pageSize: 10,
};

export const emptyFeatureDraft: LlmFeatureWriteModel = {
  featureKey: '',
  displayName: '',
  description: null,
  valueType: 'string',
  allowedValuesJson: [],
  isFilterable: true,
  isRoutable: true,
  isEnabled: true,
};

export function toFeatureQuery(filters: FeatureFilters): LlmFeatureListQuery {
  return {
    valueType: filters.valueType || undefined,
    isEnabled: filters.isEnabled === 'all' ? undefined : filters.isEnabled === 'true',
    isFilterable: filters.isFilterable === 'all' ? undefined : filters.isFilterable === 'true',
    isRoutable: filters.isRoutable === 'all' ? undefined : filters.isRoutable === 'true',
    page: filters.page,
    pageSize: filters.pageSize,
  };
}

export function toFeatureDraft(draft: LlmFeatureWriteModel): LlmFeatureWriteModel {
  return {
    ...draft,
    description: asOptionalString(draft.description ?? ''),
  };
}
