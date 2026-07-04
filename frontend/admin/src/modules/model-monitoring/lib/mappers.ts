import type { ModelOption } from '@/modules/model-management/options/api';
import type {
  ModelUsageSummaryResponse,
  ErrorRecordViewResponse,
  ModelErrorRecord,
  ModelUsageSummary,
  MonitoringOverview,
  MonitoringOverviewResponse,
  UsageRequestRow,
  UsageRequestViewResponse,
} from './contracts';

export function buildCardDisplayNameMap(options: ModelOption[] | undefined) {
  return new Map((options ?? []).map((item) => [item.modelKey, item.displayName]));
}

export function toUsageSummaryView(
  item: ModelUsageSummaryResponse,
  modelDisplayNames: Map<string, string>,
): ModelUsageSummary {
  return {
    modelKey: item.modelKey,
    displayName: modelDisplayNames.get(item.modelKey) ?? item.modelKey,
    totalRequests: item.totalRequests,
    totalInputTokens: item.totalInputTokens,
    totalOutputTokens: item.totalOutputTokens,
    averageLatencyMs: item.avgDurationMs,
    errorCount: item.errorCount,
    errorRate: item.totalRequests > 0 ? item.errorCount / item.totalRequests : 0,
  };
}

export function toUsageRequestRow(item: UsageRequestViewResponse): UsageRequestRow {
  return {
    requestId: item.requestId,
    modelKey: item.modelKey,
    capability: item.capability,
    success: item.success,
    attemptCount: item.attemptCount,
    finalInstanceKey: item.finalInstanceKey,
    errorCode: item.errorCode,
    errorMessage: item.errorMessage,
    totalInputTokens: item.totalInputTokens,
    totalOutputTokens: item.totalOutputTokens,
    totalEstimatedCost: item.totalEstimatedCost,
    totalDurationMs: item.totalDurationMs,
    startedAtUtc: item.startedAtUtc,
    completedAtUtc: item.completedAtUtc,
  };
}

export function toErrorRecordView(
  item: ErrorRecordViewResponse,
  modelDisplayNames: Map<string, string>,
): ModelErrorRecord {
  return {
    requestId: item.requestId,
    modelKey: item.modelKey,
    displayName: modelDisplayNames.get(item.modelKey) ?? item.modelKey,
    instanceKey: item.instanceKey,
    capability: item.capability,
    errorCode: item.errorCode,
    errorMessage: item.errorMessage,
    durationMs: item.durationMs,
    startedAtUtc: item.startedAtUtc,
    completedAtUtc: item.completedAtUtc,
  };
}

export function toMonitoringOverview(
  data: MonitoringOverviewResponse,
  modelDisplayNames: Map<string, string>,
): MonitoringOverview {
  return {
    totalRequests: data.totalRequests,
    totalTokens: data.totalTokens,
    averageLatencyMs: data.averageLatencyMs,
    totalErrors: data.totalErrors,
    modelSummaries: data.modelSummaries.map((item) => toUsageSummaryView(item, modelDisplayNames)),
  };
}
