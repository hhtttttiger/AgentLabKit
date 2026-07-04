import type { UsageRequestListQuery } from '../../lib/contracts';
import { toEndOfDayIso, toStartOfDayIso } from '../../lib/date-utils';

export type UsageFilters = {
  modelKey: string;
  fromDate: string;
  toDate: string;
  page: number;
  pageSize: number;
};

export const defaultUsageFilters: UsageFilters = {
  modelKey: '',
  fromDate: '',
  toDate: '',
  page: 1,
  pageSize: 10,
};

export type UsageDetailFilters = {
  fromDate: string;
  toDate: string;
  page: number;
  pageSize: number;
};

export const defaultUsageDetailFilters: UsageDetailFilters = {
  fromDate: '',
  toDate: '',
  page: 1,
  pageSize: 20,
};

export function usageFiltersFromSearchParams(searchParams: URLSearchParams): UsageFilters {
  const page = Number(searchParams.get('page') ?? defaultUsageFilters.page);
  const pageSize = Number(searchParams.get('pageSize') ?? defaultUsageFilters.pageSize);

  return {
    modelKey: searchParams.get('modelKey') ?? defaultUsageFilters.modelKey,
    fromDate: searchParams.get('fromDate') ?? defaultUsageFilters.fromDate,
    toDate: searchParams.get('toDate') ?? defaultUsageFilters.toDate,
    page: Number.isFinite(page) && page > 0 ? page : defaultUsageFilters.page,
    pageSize: Number.isFinite(pageSize) && pageSize > 0 ? pageSize : defaultUsageFilters.pageSize,
  };
}

export function usageFiltersToSearchParams(filters: UsageFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.modelKey) params.set('modelKey', filters.modelKey);
  if (filters.fromDate) params.set('fromDate', filters.fromDate);
  if (filters.toDate) params.set('toDate', filters.toDate);
  if (filters.page !== defaultUsageFilters.page) params.set('page', String(filters.page));
  if (filters.pageSize !== defaultUsageFilters.pageSize) params.set('pageSize', String(filters.pageSize));
  return params;
}

export function toUsageDetailQuery(
  modelKey: string,
  filters: UsageDetailFilters,
): UsageRequestListQuery {
  return {
    modelKey,
    from: toStartOfDayIso(filters.fromDate),
    to: toEndOfDayIso(filters.toDate),
    page: filters.page,
    pageSize: filters.pageSize,
  };
}
