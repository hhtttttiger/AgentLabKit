import type { KbStatus } from '../../lib/contracts';

export type KbListFilters = {
  page: number;
  pageSize: number;
  status: KbStatus | 'all';
  keyword: string;
};

export const defaultKbListFilters: KbListFilters = {
  page: 1,
  pageSize: 12,
  status: 'all',
  keyword: '',
};

export function toKbListQuery(filters: KbListFilters) {
  return {
    page: filters.page,
    pageSize: filters.pageSize,
    status: filters.status === 'all' ? undefined : filters.status,
    keyword: filters.keyword.trim() || undefined,
  };
}
