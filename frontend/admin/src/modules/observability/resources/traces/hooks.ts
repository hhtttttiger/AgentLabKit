import { useQuery } from '@tanstack/react-query';
import { observabilityQueryKeys } from '../../lib/queryKeys';
import {
  getIngestionHealth,
  getTraceDetail,
  getTraceStats,
  listTraces,
  type TraceListParams,
} from './api';

export function useTraceList(params: TraceListParams) {
  return useQuery({
    queryKey: observabilityQueryKeys.traces(params),
    queryFn: () => listTraces(params),
  });
}

export function useTraceDetail(traceId: string) {
  return useQuery({
    queryKey: observabilityQueryKeys.traceDetail(traceId),
    queryFn: () => getTraceDetail(traceId),
    enabled: !!traceId,
  });
}

export function useTraceStats(days = 7) {
  return useQuery({
    queryKey: observabilityQueryKeys.stats(days),
    queryFn: () => getTraceStats(days),
  });
}

export function useIngestionHealth() {
  return useQuery({
    queryKey: observabilityQueryKeys.ingestionHealth(),
    queryFn: getIngestionHealth,
    refetchInterval: 10_000,
  });
}
