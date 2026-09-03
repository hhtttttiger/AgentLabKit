/**
 * Run Mappers — Convert backend DTOs to frontend ViewModels.
 *
 * Responsibilities:
 * - Status normalization (backend status → frontend RunStatus)
 * - Null/undefined normalization
 * - Date parsing
 * - Duration normalization
 * - Optional nested objects
 */

import type { RunSummaryDto, RunDetailDto, RunEventDto, RunCostDto, RunEvaluationDto } from '../api/dto';
import type { RunSummary, RunDetail, RunEvent, RunCostSummary, RunEvaluationSummary, RunStatus } from '../types';

/**
 * Normalize backend status string to frontend RunStatus.
 */
function normalizeStatus(status: string | null | undefined): RunStatus {
  if (!status) return 'unknown';
  const lower = status.toLowerCase();
  if (lower === 'success' || lower === 'completed') return 'success';
  if (lower === 'failed' || lower === 'error') return 'failed';
  if (lower === 'running') return 'running';
  if (lower === 'queued' || lower === 'pending') return 'queued';
  if (lower === 'cancelled') return 'cancelled';
  return 'unknown';
}

/**
 * Extract token usage from the tokenUsageJson field.
 */
function extractTokenUsage(tokenUsageJson: Record<string, unknown>): {
  totalTokens: number | null;
  inputTokens: number | null;
  outputTokens: number | null;
} {
  if (!tokenUsageJson || typeof tokenUsageJson !== 'object') {
    return { totalTokens: null, inputTokens: null, outputTokens: null };
  }
  return {
    totalTokens: typeof tokenUsageJson.totalTokens === 'number' ? tokenUsageJson.totalTokens : null,
    inputTokens: typeof tokenUsageJson.inputTokens === 'number' ? tokenUsageJson.inputTokens : null,
    outputTokens: typeof tokenUsageJson.outputTokens === 'number' ? tokenUsageJson.outputTokens : null,
  };
}

/**
 * Map RunSummaryDto to RunSummary ViewModel.
 */
export function mapRunSummary(dto: RunSummaryDto): RunSummary {
  return {
    // runId is the execution identity exposed by the audit API.  Do not fall
    // back to the database row id: those are different identities.
    id: dto.runId,
    agentKey: dto.agentKey,
    agentVersion: dto.agentVersion != null ? String(dto.agentVersion) : null,
    status: normalizeStatus(dto.status),
    durationMs: dto.durationMs ?? null,
    costUsd: null, // Not available from audit endpoint
    evaluationScore: null, // Not available from audit endpoint
    startedAt: dto.createdAtUtc,
    // The audit contract does not expose a completion timestamp.  Duration is
    // not evidence from which a timestamp may be manufactured.
    completedAt: null,
    errorMessage: dto.errorMessage ?? null,
  };
}

/**
 * Map RunDetailDto to RunDetail ViewModel.
 */
export function mapRunDetail(dto: RunDetailDto): RunDetail {
  const summary = mapRunSummary(dto);
  const { totalTokens, inputTokens, outputTokens } = extractTokenUsage(dto.tokenUsageJson ?? {});

  return {
    ...summary,
    modelKey: null, // Not available from audit endpoint
    sessionId: null, // Not available from audit endpoint
    traceId: null, // Not available from audit endpoint
    input: dto.inputSummary ?? null,
    output: dto.outputSummary ?? null,
    totalTokens,
    metadata: {
      inputTokens,
      outputTokens,
      toolCallsCount: Array.isArray(dto.toolCallsJson) ? dto.toolCallsJson.length : 0,
    },
  };
}

/**
 * Map RunEventDto to RunEvent ViewModel.
 */
export function mapRunEvent(dto: RunEventDto): RunEvent {
  return {
    id: dto.id,
    sequence: dto.sequence,
    type: dto.type ?? 'unknown',
    timestamp: dto.timestamp,
    spanId: dto.spanId ?? null,
    payload: dto.payload ?? {},
    metadata: dto.metadata ?? {},
  };
}

/**
 * Map RunCostDto to RunCostSummary ViewModel.
 */
export function mapRunCost(dto: RunCostDto): RunCostSummary {
  return {
    totalUsd: dto.totalUsd,
    inputTokens: dto.inputTokens,
    outputTokens: dto.outputTokens,
    llmCalls: (dto.llmCalls ?? []).map(call => ({
      modelKey: call.modelKey,
      costUsd: call.costUsd,
      inputTokens: call.inputTokens,
      outputTokens: call.outputTokens,
    })),
  };
}

/**
 * Map RunEvaluationDto to RunEvaluationSummary ViewModel.
 */
export function mapRunEvaluation(dto: RunEvaluationDto): RunEvaluationSummary {
  return {
    overallScore: dto.overallScore ?? null,
    metrics: (dto.metrics ?? []).map(metric => ({
      name: metric.name,
      score: metric.score,
    })),
  };
}
