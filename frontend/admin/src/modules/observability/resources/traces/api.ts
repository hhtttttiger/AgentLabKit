import { apiRequest } from '@/shared/api/client';
import type {
  IngestionHealth,
  TraceDetailResponse,
  TracePage,
  TraceStatsData,
  TraceStatus,
} from '../../lib/contracts';

export interface TraceListParams {
  cursor?: string;
  limit?: number;
  agent_key?: string;
  session_id?: string;
  status?: TraceStatus;
  from_date?: string;
  to_date?: string;
}

export function listTraces(params: TraceListParams) {
  return apiRequest<TracePage>('/api/traces', { query: { ...params } });
}

export function getTraceDetail(traceId: string) {
  return apiRequest<TraceDetailResponse>(`/api/traces/${traceId}`);
}

export function getTraceStats(days = 7) {
  return apiRequest<TraceStatsData>('/api/traces/stats', { query: { days } });
}

export function getTraceByRun(runId: string) {
  return apiRequest<TraceDetailResponse>(`/api/traces/by-run/${runId}`);
}

export function getIngestionHealth() {
  return apiRequest<IngestionHealth>('/api/traces/ingestion-health');
}
