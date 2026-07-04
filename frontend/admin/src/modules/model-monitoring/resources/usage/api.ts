import { apiRequest } from '@/shared/api/client';
import type {
  ModelUsageSummaryPage,
  ModelUsageSummaryQuery,
  MonitoringOverviewResponse,
  UsageRequestListQuery,
  UsageRequestPage,
} from '../../lib/contracts';

export function fetchOverview(query: Omit<ModelUsageSummaryQuery, 'page' | 'pageSize'>) {
  return apiRequest<MonitoringOverviewResponse>('/api/model-usage/statistics/overview', { query });
}

export function listUsageSummaries(query: ModelUsageSummaryQuery) {
  return apiRequest<ModelUsageSummaryPage>('/api/model-usage/statistics/models', { query });
}

export function listUsageRequests(query: UsageRequestListQuery) {
  return apiRequest<UsageRequestPage>('/api/model-usage/requests', { query });
}
