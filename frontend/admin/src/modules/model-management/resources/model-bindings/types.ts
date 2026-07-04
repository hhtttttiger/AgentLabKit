import type { CardCapability, LlmModelBindingListQuery, LlmModelBindingWriteModel } from '../../lib/contracts';

export type ModelBindingFilters = {
  capability: '' | CardCapability;
  modelKey: string;
  isEnabled: 'all' | 'true' | 'false';
  page: number;
  pageSize: number;
};

export const defaultModelBindingFilters: ModelBindingFilters = {
  capability: '',
  modelKey: '',
  isEnabled: 'all',
  page: 1,
  pageSize: 10,
};

export const emptyModelBindingDraft: LlmModelBindingWriteModel = {
  bindingKey: '',
  displayName: '',
  capability: 'Text',
  modelKey: '',
  metadataJson: {},
  isEnabled: true,
};

export function toModelBindingQuery(filters: ModelBindingFilters): LlmModelBindingListQuery {
  return {
    capability: filters.capability || undefined,
    modelKey: filters.modelKey.trim() || undefined,
    isEnabled: filters.isEnabled === 'all' ? undefined : filters.isEnabled === 'true',
    page: filters.page,
    pageSize: filters.pageSize,
  };
}
