export interface TraceData {
  traceId: string;
  rootSpanId: string;
  agentKey: string | null;
  sessionId: string | null;
  status: string;
  totalDurationMs: number | null;
  totalInputTokens: number;
  totalOutputTokens: number;
  totalEstimatedCost: number;
  spanCount: number;
  startedAtUtc: string;
  completedAtUtc: string | null;
}

export interface SpanData {
  spanId: string;
  traceId: string;
  parentSpanId: string | null;
  spanKind: string;
  name: string;
  status: string;
  startedAtUtc: string | null;
  completedAtUtc: string | null;
  durationMs: number | null;
  attributes: Record<string, unknown>;
  errorCode: string | null;
  errorMessage: string | null;
}

export interface TraceDetailResponse {
  trace: TraceData;
  spans: SpanData[];
}

export interface TraceStatsData {
  totalTraces: number;
  avgDurationMs: number;
  totalTokens: number;
  errorCount: number;
}

export type PagedResult<T> = {
  items: T[];
  totalCount: number;
  page: number;
  pageSize: number;
};
