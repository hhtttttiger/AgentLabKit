import type { AuditListQuery } from '../../lib/contracts';

export type AuditFilters = {
  page: number;
  pageSize: number;
};

export const defaultAuditFilters: AuditFilters = {
  page: 1,
  pageSize: 10,
};

export function toAuditListQuery(filters: AuditFilters): AuditListQuery {
  return {
    page: filters.page,
    pageSize: filters.pageSize,
  };
}
