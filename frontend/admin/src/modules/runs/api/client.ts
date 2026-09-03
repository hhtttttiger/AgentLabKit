/**
 * Runs API — Client functions for the Runs module.
 *
 * These functions call backend endpoints and return raw DTOs.
 * Use mappers to convert to ViewModels.
 */

import { apiRequest } from '@/shared/api/client';
import type {
  RunListResponseDto,
  RunDetailDto,
  RunEventsResponseDto,
  RunCostDto,
  RunEvaluationDto,
} from './dto';
import type { RunFilters } from '../types';

/**
 * List runs with optional filters.
 */
export async function listRuns(filters?: RunFilters): Promise<RunListResponseDto> {
  const params = new URLSearchParams();
  if (filters?.agentKey) params.set('agent', filters.agentKey);
  if (filters?.status) params.set('status', filters.status);
  if (filters?.modelKey) params.set('model', filters.modelKey);
  if (filters?.startTime) params.set('start', filters.startTime);
  if (filters?.endTime) params.set('end', filters.endTime);
  if (filters?.hasError !== undefined) params.set('hasError', String(filters.hasError));
  if (filters?.evaluationStatus) params.set('evalStatus', filters.evaluationStatus);

  const query = params.toString();
  const url = `/api/runs${query ? `?${query}` : ''}`;

  return apiRequest<RunListResponseDto>(url);
}

/**
 * Get a single run by ID.
 */
export async function getRun(runId: string): Promise<RunDetailDto> {
  return apiRequest<RunDetailDto>(`/api/runs/${runId}`);
}

/**
 * Get events for a run.
 */
export async function getRunEvents(runId: string): Promise<RunEventsResponseDto> {
  return apiRequest<RunEventsResponseDto>(`/api/runs/${runId}/events`);
}

/**
 * Get cost breakdown for a run.
 */
export async function getRunCost(runId: string): Promise<RunCostDto> {
  return apiRequest<RunCostDto>(`/api/runs/${runId}/cost`);
}

/**
 * Get evaluation results for a run.
 */
export async function getRunEvaluation(runId: string): Promise<RunEvaluationDto> {
  return apiRequest<RunEvaluationDto>(`/api/runs/${runId}/evaluation`);
}

/**
 * Replay a run — re-execute with the same input.
 */
export async function replayRun(runId: string): Promise<RunDetailDto> {
  return apiRequest<RunDetailDto>(`/api/runs/${runId}/replay`, { method: 'POST' });
}
