export type TraceStatus = 'ok' | 'error' | 'timeout' | 'cancelled';

export interface TraceData {
  traceId: string;
  rootSpanId: string;
  runId: string;
  agentKey: string | null;
  sessionId: string | null;
  userId: string | null;
  correlationId: string | null;
  status: TraceStatus;
  totalDurationMs: number;
  totalInputTokens: number;
  totalOutputTokens: number;
  cacheWriteTokens: number;
  cacheReadTokens: number;
  totalEstimatedCost: number;
  spanCount: number;
  droppedSpanCount: number;
  sampleReason: string;
  attributes: Record<string, unknown>;
  schemaVersion: number;
  startedAtUtc: string;
  completedAtUtc: string;
}

export interface SpanData {
  spanId: string;
  traceId: string;
  parentSpanId: string | null;
  name: string;
  kind: string;
  status: TraceStatus;
  instrumentationScope: string;
  startedAtUtc: string;
  completedAtUtc: string;
  durationMs: number;
  attributes: Record<string, unknown>;
  events: Array<Record<string, unknown>>;
  links: Array<Record<string, unknown>>;
  errorCode: string | null;
  errorMessage: string | null;
}

export interface TraceDetailResponse {
  trace: TraceData;
  spans: SpanData[];
}

export interface TraceStatsData {
  totalTraces: number;
  errorCount: number;
  timeoutCount: number;
  cancelledCount: number;
  p50DurationMs: number;
  p95DurationMs: number;
  totalTokens: number;
  totalEstimatedCost: number;
}

export interface TracePage {
  items: TraceData[];
  nextCursor: string | null;
}

export interface IngestionHealth {
  publisher: {
    published: number;
    retried: number;
    dropped: number;
    queueDepth: number;
    activeTraces: number;
    bufferedSpans: number;
    bufferOverflowDropped: number;
  };
  queue: {
    backlog: number;
    pending: number;
    delayed: number;
    deadLetter: number;
    consumers: number;
    available: number;
  } | null;
  workerTasks: Record<string, {
    backlog: number;
    pending: number;
    delayed: number;
    deadLetter: number;
    consumers: number;
    available: number;
  }>;
}
