import { apiRequest } from '@/shared/api/client';
import type { LlmFeatureOptionView } from '../lib/contracts';

export type ModelOption = {
  modelKey: string;
  modelName: string;
  displayName: string;
  isEnabled: boolean;
};

export type ConnectionProfileOption = {
  profileKey: string;
  displayName: string;
  provider: string;
  baseUrl: string | null;
  webSocketBaseUrl: string | null;
  isEnabled: boolean;
};

export type ProviderModelOptions = {
  connectionProfileKey: string;
  provider: string;
  models: string[];
  deployments: string[];
};

export type FeatureOption = LlmFeatureOptionView;

export function listModelOptions() {
  return apiRequest<ModelOption[]>('/api/llm-catalog/options/models');
}

export function listConnectionProfileOptions() {
  return apiRequest<ConnectionProfileOption[]>('/api/llm-catalog/options/connection-profiles');
}

export function getProviderModelOptions(connectionProfileKey: string) {
  return apiRequest<ProviderModelOptions>(`/api/llm-catalog/connection-profiles/${encodeURIComponent(connectionProfileKey)}/provider-models`);
}

export function listFeatureOptions() {
  return apiRequest<FeatureOption[]>('/api/llm-catalog/options/features');
}
