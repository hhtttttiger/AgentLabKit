import { useQuery } from '@tanstack/react-query';
import { observabilityQueryKeys } from '../../lib/queryKeys';
import { listTraces, getTraceDetail, getTraceTimeline, getTraceStats } from './api';

export function useTraceList(params: { page?: number; pageSize?: number; agent_key?: string; status?: string; days?: number }) {
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

export function useTraceTimeline(traceId: string) {
  return useQuery({
    queryKey: observabilityQueryKeys.traceTimeline(traceId),
    queryFn: () => getTraceTimeline(traceId),
    enabled: !!traceId,
  });
}

export function useTraceStats(days = 7) {
  return useQuery({
    queryKey: observabilityQueryKeys.stats(days),
    queryFn: () => getTraceStats(days),
  });
}
