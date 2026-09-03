/**
 * Run DTOs — Backend response types.
 *
 * These match the backend API response format (camelCase via CamelModel).
 * They are NOT frontend view models — use mappers to convert.
 */

export interface RunSummaryDto {
  id: string;
  agentKey: string;
  runId: string;
  agentVersion: number | null;
  inputSummary: string | null;
  outputSummary: string | null;
  status: string;
  durationMs: number | null;
  tokenUsageJson: Record<string, unknown>;
  errorMessage: string | null;
  createdAtUtc: string | null;
}

export interface RunDetailDto extends RunSummaryDto {
  toolCallsJson: unknown[];
}

export interface RunEventDto {
  id: string;
  sequence: number;
  type: string;
  timestamp: string | null;
  spanId: string | null;
  payload: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export interface RunCostDto {
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

export interface RunEvaluationDto {
  overallScore: number | null;
  metrics: Array<{
    name: string;
    score: number | null;
  }>;
}

export interface RunListResponseDto {
  items: RunSummaryDto[];
  total: number;
}

export interface RunEventsResponseDto {
  items: RunEventDto[];
}
