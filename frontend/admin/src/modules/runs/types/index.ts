/**
 * Run types — View models for the Runs module.
 *
 * These are frontend view models that map backend DTOs to UI-friendly shapes.
 * They are NOT backend domain entities.
 */

export type RunStatus = 'success' | 'failed' | 'running' | 'queued' | 'cancelled' | 'unknown';

export interface RunSummary {
  id: string;
  agentKey: string;
  agentVersion: string | null;
  status: RunStatus;
  durationMs: number | null;
  costUsd: number | null;
  evaluationScore: number | null;
  startedAt: string | null;
  completedAt: string | null;
  errorMessage: string | null;
}

export interface RunDetail extends RunSummary {
  modelKey: string | null;
  sessionId: string | null;
  traceId: string | null;
  input: string | null;
  output: string | null;
  totalTokens: number | null;
  metadata: Record<string, unknown>;
}

export interface RunTimelineItem {
  id: string;
  type: 'llm' | 'tool' | 'run' | 'error' | 'note';
  title: string;
  status: string;
  durationMs: number | null;
  startedAt: string | null;
  metadata: Record<string, unknown>;
}

export interface RunEvent {
  id: string;
  sequence: number | null;
  type: string;
  timestamp: string | null;
  spanId: string | null;
  payload: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export interface RunCostSummary {
  totalUsd: number | null;
  inputTokens: number | null;
  outputTokens: number | null;
  llmCalls: Array<{
    modelKey: string;
    costUsd: number | null;
    inputTokens: number | null;
    outputTokens: number | null;
  }>;
}

export interface RunEvaluationSummary {
  overallScore: number | null;
  metrics: Array<{
    name: string;
    score: number | null;
  }>;
}

export interface RunFilters {
  agentKey?: string;
  status?: RunStatus;
  modelKey?: string;
  startTime?: string;
  endTime?: string;
  hasError?: boolean;
  evaluationStatus?: 'pass' | 'fail' | 'none';
}
