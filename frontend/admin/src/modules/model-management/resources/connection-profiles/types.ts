import type { LlmConnectionProfileListQuery, LlmConnectionProfileWriteModel, LlmProvider } from '../../lib/contracts';
import { asOptionalString } from '../../lib/forms';

export type ConnectionProfileFilters = {
  provider: '' | LlmProvider;
  isEnabled: 'all' | 'true' | 'false';
  page: number;
  pageSize: number;
};

export const defaultConnectionProfileFilters: ConnectionProfileFilters = {
  provider: '',
  isEnabled: 'all',
  page: 1,
  pageSize: 10,
};

export const emptyConnectionProfileDraft: LlmConnectionProfileWriteModel = {
  profileKey: '',
  displayName: '',
  provider: 'openai',
  baseUrl: null,
  webSocketBaseUrl: null,
  apiVersion: null,
  region: null,
  extraJson: {},
  isEnabled: true,
};

export function toConnectionProfileQuery(filters: ConnectionProfileFilters): LlmConnectionProfileListQuery {
  return {
    provider: filters.provider || undefined,
    isEnabled: filters.isEnabled === 'all' ? undefined : filters.isEnabled === 'true',
    page: filters.page,
    pageSize: filters.pageSize,
  };
}

export function toConnectionProfileDraft(draft: LlmConnectionProfileWriteModel): LlmConnectionProfileWriteModel {
  return {
    ...draft,
    baseUrl: asOptionalString(draft.baseUrl ?? ''),
    webSocketBaseUrl: asOptionalString(draft.webSocketBaseUrl ?? ''),
    apiVersion: asOptionalString(draft.apiVersion ?? ''),
    region: asOptionalString(draft.region ?? ''),
  };
}
