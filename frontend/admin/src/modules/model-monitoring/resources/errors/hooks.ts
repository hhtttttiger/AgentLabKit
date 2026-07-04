import { useQuery } from '@tanstack/react-query';
import type { ErrorRecordListQuery } from '../../lib/contracts';
import { modelMonitoringQueryKeys } from '../../lib/queryKeys';
import { fetchDistinctErrorCodes } from './api';
import { listErrors } from './api';

export function useErrorList(query: ErrorRecordListQuery) {
  return useQuery({
    queryKey: modelMonitoringQueryKeys.errors('list', query),
    queryFn: () => listErrors(query),
  });
}

export function useDistinctErrorCodes() {
  return useQuery({
    queryKey: modelMonitoringQueryKeys.errors('distinctErrorCodes'),
    queryFn: () => fetchDistinctErrorCodes(),
    staleTime: 60_000,
  });
}
