import type { RunDetailDto } from '../api/dto';
import type { RunDetail, RunStatus } from '../types';

const CANONICAL_STATUSES: RunStatus[] = ['running', 'completed', 'failed', 'cancelled'];

function normalizeStatus(status: string | null | undefined): RunStatus {
  return status && CANONICAL_STATUSES.includes(status.toLowerCase() as RunStatus)
    ? status.toLowerCase() as RunStatus
    : 'unknown';
}

function asText(value: unknown): string | null {
  return typeof value === 'string' ? value : value == null ? null : JSON.stringify(value);
}

export function mapRunDetail(dto: RunDetailDto): RunDetail {
  const usage = dto.metadata?.usage;
  const usageObject = usage && typeof usage === 'object' ? usage as Record<string, unknown> : {};
  return {
    id: dto.runId,
    agentKey: dto.targetKey ?? '—',
    agentVersion: dto.targetVersion,
    status: normalizeStatus(dto.status),
    durationMs: dto.durationMs,
    costUsd: null,
    evaluationScore: null,
    startedAt: dto.startedAt,
    completedAt: dto.completedAt,
    modelKey: null,
    sessionId: dto.sessionId,
    traceId: dto.traceId,
    input: asText(dto.input),
    output: asText(dto.output),
    totalTokens: typeof usageObject.totalTokens === 'number' ? usageObject.totalTokens : null,
    metadata: dto.metadata ?? {},
    errorMessage: dto.errorMessage,
  };
}
