import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useModelOptions } from '@/modules/model-management/options/hooks';
import type { ModelErrorRecord } from '../../lib/contracts';
import { buildCardDisplayNameMap, toErrorRecordView } from '../../lib/mappers';
import { useErrorList } from './hooks';
import {
  defaultErrorFilters,
  errorFiltersFromSearchParams,
  errorFiltersToSearchParams,
  toErrorListQuery,
  type ErrorFilters,
} from './types';

export type ErrorsPageState = {
  filters: ErrorFilters;
  modelOptionsQuery: ReturnType<typeof useModelOptions>;
  listQuery: ReturnType<typeof useErrorList>;
  rows: ModelErrorRecord[];
  expandedRowId: string | null;
  patchFilters: (patch: Partial<ErrorFilters>) => void;
  resetFilters: () => void;
  setPage: (page: number) => void;
  toggleExpand: (id: string) => void;
};

export function useErrorsPageState(): ErrorsPageState {
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = errorFiltersFromSearchParams(searchParams);
  const [expandedRowId, setExpandedRowId] = useState<string | null>(null);

  const modelOptionsQuery = useModelOptions();
  const cardDisplayNames = buildCardDisplayNameMap(modelOptionsQuery.data);

  const query = toErrorListQuery(filters);
  const listQuery = useErrorList(query);
  const rows = (listQuery.data?.items ?? []).map((item) => toErrorRecordView(item, cardDisplayNames));

  function updateFilters(next: ErrorFilters) {
    setSearchParams(errorFiltersToSearchParams(next), { replace: true });
  }

  return {
    filters,
    modelOptionsQuery,
    listQuery,
    rows,
    expandedRowId,
    patchFilters: (patch) => updateFilters({ ...filters, ...patch }),
    resetFilters: () => updateFilters(defaultErrorFilters),
    setPage: (page) => updateFilters({ ...filters, page }),
    toggleExpand: (id) => setExpandedRowId((prev) => (prev === id ? null : id)),
  };
}
