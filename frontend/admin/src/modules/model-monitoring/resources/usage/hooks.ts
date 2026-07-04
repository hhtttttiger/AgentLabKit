import { useQuery } from '@tanstack/react-query';
import type { ModelUsageSummaryQuery, UsageRequestListQuery } from '../../lib/contracts';
import { modelMonitoringQueryKeys } from '../../lib/queryKeys';
import { fetchOverview, listUsageRequests, listUsageSummaries } from './api';

export function useMonitoringOverview(query: Omit<ModelUsageSummaryQuery, 'page' | 'pageSize'>) {
  return useQuery({
    queryKey: modelMonitoringQueryKeys.usage('overview', query),
    queryFn: () => fetchOverview(query),
    staleTime: 30_000,
  });
}

export function useUsageSummaryList(query: ModelUsageSummaryQuery) {
  return useQuery({
    queryKey: modelMonitoringQueryKeys.usage('list', query),
    queryFn: () => listUsageSummaries(query),
  });
}

export function useUsageRequests(query: UsageRequestListQuery, enabled = true) {
  return useQuery({
    queryKey: modelMonitoringQueryKeys.usage('requests', query),
    queryFn: () => listUsageRequests(query),
    enabled,
  });
}
