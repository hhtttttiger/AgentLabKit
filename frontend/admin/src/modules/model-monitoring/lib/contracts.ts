import type { PagedResult } from '@/shared/types/paging';

export type ModelUsageCapability = 'Text' | 'Multimodal' | 'Embedding' | 'Speech' | 'Image' | 'Tool';

export type ModelUsageSummaryResponse = {
  modelKey: string;
  totalRequests: number;
  successCount: number;
  errorCount: number;
  totalInputTokens: number;
  totalOutputTokens: number;
  totalEstimatedCost: number;
  avgDurationMs: number;
  totalCacheWriteTokens: number;
  totalCacheReadTokens: number;
};

export type UsageRequestViewResponse = {
  requestId: string;
  modelKey: string;
  capability: ModelUsageCapability;
  success: boolean;
  attemptCount: number;
  finalInstanceKey: string | null;
  errorCode: string | null;
  errorMessage: string | null;
  totalInputTokens: number;
  totalOutputTokens: number;
  totalEstimatedCost: number;
  totalDurationMs: number;
  cacheWriteTokens: number;
  cacheReadTokens: number;
  startedAtUtc: string;
  completedAtUtc: string;
};

export type ErrorRecordViewResponse = {
  requestId: string;
  modelKey: string;
  instanceKey: string | null;
  capability: ModelUsageCapability | null;
  errorCode: string | null;
  errorMessage: string | null;
  durationMs: number;
  startedAtUtc: string;
  completedAtUtc: string;
};

export type ModelUsageSummaryQuery = {
  from?: string;
  to?: string;
  modelKey?: string;
  page: number;
  pageSize: number;
};

export type UsageRequestListQuery = {
  from?: string;
  to?: string;
  modelKey?: string;
  page: number;
  pageSize: number;
};

export type ErrorRecordListQuery = {
  from?: string;
  to?: string;
  modelKey?: string;
  errorCode?: string;
  page: number;
  pageSize: number;
};

export type MonitoringOverviewResponse = {
  totalRequests: number;
  totalTokens: number;
  totalErrors: number;
  averageLatencyMs: number;
  modelSummaries: ModelUsageSummaryResponse[];
};

export type DistinctErrorCodesResponse = {
  errorCodes: string[];
};

export type ModelUsageSummary = {
  modelKey: string;
  displayName: string;
  totalRequests: number;
  totalInputTokens: number;
  totalOutputTokens: number;
  averageLatencyMs: number;
  errorCount: number;
  errorRate: number;
};

export type UsageRequestRow = {
  requestId: string;
  modelKey: string;
  capability: ModelUsageCapability;
  success: boolean;
  attemptCount: number;
  finalInstanceKey: string | null;
  errorCode: string | null;
  errorMessage: string | null;
  totalInputTokens: number;
  totalOutputTokens: number;
  totalEstimatedCost: number;
  totalDurationMs: number;
  startedAtUtc: string;
  completedAtUtc: string;
};

export type ModelErrorRecord = {
  requestId: string;
  modelKey: string;
  displayName: string;
  instanceKey: string | null;
  capability: ModelUsageCapability | null;
  errorCode: string | null;
  errorMessage: string | null;
  durationMs: number;
  startedAtUtc: string;
  completedAtUtc: string;
};

export type MonitoringOverview = {
  totalRequests: number;
  totalTokens: number;
  averageLatencyMs: number;
  totalErrors: number;
  modelSummaries: ModelUsageSummary[];
};

export type ModelUsageSummaryPage = PagedResult<ModelUsageSummaryResponse>;
export type UsageRequestPage = PagedResult<UsageRequestViewResponse>;
export type ErrorRecordPage = PagedResult<ErrorRecordViewResponse>;
