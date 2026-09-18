import { apiRequest } from '@/shared/api/client';

export type DesktopModelSettings = {
  provider: string;
  baseUrl: string;
  model: string;
  apiKeyConfigured: boolean;
  providerOverridden: boolean;
  baseUrlOverridden: boolean;
  apiKeyOverridden: boolean;
  modelOverridden: boolean;
  overrideEnvironment: Record<string, string>;
};

export type DesktopModelSettingsDraft = {
  provider: string;
  baseUrl: string;
  model: string;
  apiKey?: string;
  clearApiKey?: boolean;
};

export function getDesktopModelSettings() {
  return apiRequest<DesktopModelSettings>('/api/desktop/settings/models');
}

export function saveDesktopModelSettings(draft: DesktopModelSettingsDraft) {
  return apiRequest<DesktopModelSettings>('/api/desktop/settings/models', { method: 'PUT', body: draft });
}

export function testDesktopModelSettings(draft: DesktopModelSettingsDraft) {
  return apiRequest<{ status: string }>('/api/desktop/settings/models/test', { method: 'POST', body: draft });
}
