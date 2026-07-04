export type { PagedResult as LlmPagedResult } from '@/shared/types/paging';

export type LlmProvider = 'openai' | 'azure_openai';
export type CardCapability = 'Text' | 'Multimodal' | 'Embedding' | 'SpeechBatch' | 'SpeechStream' | 'Realtime' | 'Image' | 'Tool';

export type LlmConnectionProfileWriteModel = {
  profileKey: string;
  displayName: string;
  provider: LlmProvider;
  baseUrl: string | null;
  webSocketBaseUrl: string | null;
  apiVersion: string | null;
  region: string | null;
  extraJson: Record<string, unknown>;
  isEnabled: boolean;
};

export type LlmConnectionProfileView = LlmConnectionProfileWriteModel;

export type LlmConnectionProfileListQuery = {
  provider?: LlmProvider;
  isEnabled?: boolean;
  page: number;
  pageSize: number;
};

export type LlmModelWriteModel = {
  modelKey: string;
  type: CardCapability;
  modelName: string;
  displayName: string;
  description: string | null;
  connectionProfileKey: string;
  tagsJson: unknown[];
  routingPolicyJson: Record<string, unknown>;
  retryPolicyJson: Record<string, unknown>;
  isEnabled: boolean;
  inputPricePerMtok?: number;
  outputPricePerMtok?: number;
  cacheWritePricePerMtok?: number;
  cacheReadPricePerMtok?: number;
};

export type LlmModelInstanceWriteModel = {
  instanceKey: string;
  providerDeploymentName: string | null;
  region: string | null;
  priority: number;
  weight: number;
  defaultTimeoutMs: number;
  extraJson: Record<string, unknown>;
  isEnabled: boolean;
  isHealthy: boolean;
  apiKey: string | null;
};

export type LlmFeatureOptionView = {
  featureKey: string;
  displayName: string;
  valueType: string;
  allowedValuesJson: unknown[];
  isEnabled: boolean;
  isFilterable: boolean;
  isRoutable: boolean;
};

export type LlmFeatureWriteModel = {
  featureKey: string;
  displayName: string;
  description: string | null;
  valueType: string;
  allowedValuesJson: unknown[];
  isFilterable: boolean;
  isRoutable: boolean;
  isEnabled: boolean;
};

export type LlmFeatureView = LlmFeatureWriteModel;

export type LlmFeatureListQuery = {
  valueType?: string;
  isEnabled?: boolean;
  isFilterable?: boolean;
  isRoutable?: boolean;
  page: number;
  pageSize: number;
};

export type LlmModelFeatureWriteModel = {
  featureKey: string;
  isSupported: boolean;
  valueJson: unknown;
  source: string;
  remark: string | null;
};

export type LlmModelFeatureView = {
  modelKey: string;
  featureKey: string;
  displayName: string;
  valueType: string;
  allowedValuesJson: unknown[];
  isSupported: boolean;
  valueJson: unknown;
  source: string;
  remark: string | null;
};

export type LlmModelInstanceView = {
  instanceKey: string;
  providerDeploymentName: string | null;
  region: string | null;
  priority: number;
  weight: number;
  defaultTimeoutMs: number;
  extraJson: Record<string, unknown>;
  isEnabled: boolean;
  isHealthy: boolean;
  modelKey: string;
  type: CardCapability;
  modelName: string;
};

export type LlmModelBindingWriteModel = {
  bindingKey: string;
  displayName: string;
  capability: CardCapability;
  modelKey: string;
  metadataJson: Record<string, unknown>;
  isEnabled: boolean;
};

export type LlmModelBindingView = LlmModelBindingWriteModel;

export type LlmModelView = LlmModelWriteModel & {
  instances: LlmModelInstanceView[];
  bindings: LlmModelBindingView[];
  features: LlmModelFeatureView[];
  instanceCount: number;
  healthyInstanceCount: number;
};

export type LlmModelListQuery = {
  featureKey?: string;
  featureIsSupported?: boolean;
  featureValueJson?: string;
  isEnabled?: boolean;
  page: number;
  pageSize: number;
};

export type LlmModelInstanceListQuery = {
  modelKey?: string;
  featureKey?: string;
  featureIsSupported?: boolean;
  featureValueJson?: string;
  type?: CardCapability;
  isEnabled?: boolean;
  isHealthy?: boolean;
  page: number;
  pageSize: number;
};

export type LlmModelBindingListQuery = {
  capability?: CardCapability;
  modelKey?: string;
  isEnabled?: boolean;
  page: number;
  pageSize: number;
};
