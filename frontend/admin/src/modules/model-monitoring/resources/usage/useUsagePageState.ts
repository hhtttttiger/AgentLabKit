import { useState, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useModelOptions } from '@/modules/model-management/options/hooks';
import type { ModelUsageSummary, MonitoringOverview, UsageRequestRow } from '../../lib/contracts';
import { buildCardDisplayNameMap, toMonitoringOverview, toUsageRequestRow } from '../../lib/mappers';
import { toEndOfDayIso, toStartOfDayIso } from '../../lib/date-utils';
import { useMonitoringOverview, useUsageRequests } from './hooks';
import {
  defaultUsageDetailFilters,
  defaultUsageFilters,
  toUsageDetailQuery,
  type UsageDetailFilters,
  type UsageFilters,
  usageFiltersFromSearchParams,
  usageFiltersToSearchParams,
} from './types';

export type UsagePageState = {
  filters: UsageFilters;
  modelOptionsQuery: ReturnType<typeof useModelOptions>;
  overviewQuery: ReturnType<typeof useMonitoringOverview>;
  overview: MonitoringOverview;
  rows: ModelUsageSummary[];
  detail: {
    open: boolean;
    modelKey: string;
    filters: UsageDetailFilters;
    query: ReturnType<typeof useUsageRequests>;
    rows: UsageRequestRow[];
    patchFilters: (patch: Partial<UsageDetailFilters>) => void;
    setPage: (page: number) => void;
    onClose: () => void;
  };
  patchFilters: (patch: Partial<UsageFilters>) => void;
  resetFilters: () => void;
  setPage: (page: number) => void;
  openDetail: (modelKey: string) => void;
};

const emptyOverview: MonitoringOverview = {
  totalRequests: 0,
  totalTokens: 0,
  averageLatencyMs: 0,
  totalErrors: 0,
  modelSummaries: [],
};

export function useUsagePageState(): UsagePageState {
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = usageFiltersFromSearchParams(searchParams);
  const [detailModelKey, setDetailModelKey] = useState('');
  const [detailFilters, setDetailFilters] = useState<UsageDetailFilters>(defaultUsageDetailFilters);

  const modelOptionsQuery = useModelOptions();
  const cardDisplayNames = buildCardDisplayNameMap(modelOptionsQuery.data);

  // Single overview query replaces the old listQuery + overviewQuery dual-fetch.
  // Global totals come from the API; per-model rows are client-side paginated.
  const overviewQuery = useMonitoringOverview({
    modelKey: filters.modelKey.trim() || undefined,
    from: toStartOfDayIso(filters.fromDate),
    to: toEndOfDayIso(filters.toDate),
  });
  const overview = overviewQuery.data
    ? toMonitoringOverview(overviewQuery.data, cardDisplayNames)
    : emptyOverview;

  // Client-side pagination from the overview's modelSummaries
  const rows = useMemo(() => {
    const start = (filters.page - 1) * filters.pageSize;
    return overview.modelSummaries.slice(start, start + filters.pageSize);
  }, [overview.modelSummaries, filters.page, filters.pageSize]);

  const detailQueryInput = toUsageDetailQuery(detailModelKey, detailFilters);
  const detailQuery = useUsageRequests(detailQueryInput, Boolean(detailModelKey));
  const detailRows = (detailQuery.data?.items ?? []).map(toUsageRequestRow);

  function updateFilters(next: UsageFilters) {
    setSearchParams(usageFiltersToSearchParams(next), { replace: true });
  }

  return {
    filters,
    modelOptionsQuery,
    overviewQuery,
    overview,
    rows,
    detail: {
      open: Boolean(detailModelKey),
      modelKey: detailModelKey,
      filters: detailFilters,
      query: detailQuery,
      rows: detailRows,
      patchFilters: (patch) =>
        setDetailFilters((prev) => ({
          ...prev,
          ...patch,
        })),
      setPage: (page) => setDetailFilters((prev) => ({ ...prev, page })),
      onClose: () => {
        setDetailModelKey('');
        setDetailFilters(defaultUsageDetailFilters);
      },
    },
    patchFilters: (patch) =>
      updateFilters({
        ...filters,
        ...patch,
      }),
    resetFilters: () => updateFilters(defaultUsageFilters),
    setPage: (page) => updateFilters({ ...filters, page }),
    openDetail: (modelKey) => {
      setDetailModelKey(modelKey);
      setDetailFilters(defaultUsageDetailFilters);
    },
  };
}
