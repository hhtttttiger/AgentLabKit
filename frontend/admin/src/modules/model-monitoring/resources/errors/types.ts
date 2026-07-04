import type { ErrorRecordListQuery } from '../../lib/contracts';
import { toEndOfDayIso, toStartOfDayIso } from '../../lib/date-utils';

export type ErrorFilters = {
  modelKey: string;
  errorCode: string;
  fromDate: string;
  toDate: string;
  page: number;
  pageSize: number;
};

export const defaultErrorFilters: ErrorFilters = {
  modelKey: '',
  errorCode: '',
  fromDate: '',
  toDate: '',
  page: 1,
  pageSize: 20,
};

export function errorFiltersFromSearchParams(searchParams: URLSearchParams): ErrorFilters {
  const page = Number(searchParams.get('page') ?? defaultErrorFilters.page);
  const pageSize = Number(searchParams.get('pageSize') ?? defaultErrorFilters.pageSize);

  return {
    modelKey: searchParams.get('modelKey') ?? defaultErrorFilters.modelKey,
    errorCode: searchParams.get('errorCode') ?? defaultErrorFilters.errorCode,
    fromDate: searchParams.get('fromDate') ?? defaultErrorFilters.fromDate,
    toDate: searchParams.get('toDate') ?? defaultErrorFilters.toDate,
    page: Number.isFinite(page) && page > 0 ? page : defaultErrorFilters.page,
    pageSize: Number.isFinite(pageSize) && pageSize > 0 ? pageSize : defaultErrorFilters.pageSize,
  };
}

export function errorFiltersToSearchParams(filters: ErrorFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.modelKey) params.set('modelKey', filters.modelKey);
  if (filters.errorCode) params.set('errorCode', filters.errorCode);
  if (filters.fromDate) params.set('fromDate', filters.fromDate);
  if (filters.toDate) params.set('toDate', filters.toDate);
  if (filters.page !== defaultErrorFilters.page) params.set('page', String(filters.page));
  if (filters.pageSize !== defaultErrorFilters.pageSize) params.set('pageSize', String(filters.pageSize));
  return params;
}

export function toErrorListQuery(filters: ErrorFilters): ErrorRecordListQuery {
  return {
    modelKey: filters.modelKey.trim() || undefined,
    errorCode: filters.errorCode.trim() || undefined,
    from: toStartOfDayIso(filters.fromDate),
    to: toEndOfDayIso(filters.toDate),
    page: filters.page,
    pageSize: filters.pageSize,
  };
}
