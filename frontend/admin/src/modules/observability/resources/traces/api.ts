import { apiRequest } from '@/shared/api/client';
import type { TraceData, TraceDetailResponse, TraceStatsData, SpanData, PagedResult } from '../../lib/contracts';

export function listTraces(params: {
  page?: number;
  pageSize?: number;
  agent_key?: string;
  status?: string;
  days?: number;
}) {
  return apiRequest<PagedResult<TraceData>>('/api/traces', { query: params });
}

export function getTraceDetail(traceId: string) {
  return apiRequest<TraceDetailResponse>(`/api/traces/${traceId}`);
}

export function getTraceTimeline(traceId: string) {
  return apiRequest<SpanData[]>(`/api/traces/${traceId}/timeline`);
}

export function getTraceStats(days = 7) {
  return apiRequest<TraceStatsData>('/api/traces/stats', { query: { days } });
}
