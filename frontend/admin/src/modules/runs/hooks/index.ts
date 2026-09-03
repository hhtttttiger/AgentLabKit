/**
 * Runs hooks — React Query hooks for the Runs module.
 *
 * All hooks return ViewModels (not DTOs).
 * Mappers are applied in the queryFn.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getTraceByRun } from '@/modules/observability/resources/traces/api';
import { listRuns, getRun, getRunEvents, getRunCost, getRunEvaluation, replayRun } from '../api/client';
import { mapRunSummary, mapRunDetail, mapRunEvent, mapRunCost, mapRunEvaluation } from '../mappers/runMapper';
import { mapTraceToAgentExecution } from '../mappers/traceMapper';
import type { RunFilters } from '../types';

// Query key factory
export const runKeys = {
  all: ['runs'] as const,
  lists: () => [...runKeys.all, 'list'] as const,
  list: (filters?: RunFilters) => [...runKeys.lists(), filters] as const,
  details: () => [...runKeys.all, 'detail'] as const,
  detail: (runId: string) => [...runKeys.details(), runId] as const,
  events: (runId: string) => [...runKeys.detail(runId), 'events'] as const,
  trace: (runId: string) => [...runKeys.detail(runId), 'trace'] as const,
  cost: (runId: string) => [...runKeys.detail(runId), 'cost'] as const,
  evaluation: (runId: string) => [...runKeys.detail(runId), 'evaluation'] as const,
};

/**
 * Hook to list runs with optional filters.
 * Returns ViewModel (RunSummary[]).
 */
export function useRunList(filters?: RunFilters) {
  return useQuery({
    queryKey: runKeys.list(filters),
    queryFn: async () => {
      const dto = await listRuns(filters);
      return {
        items: dto.items.map(mapRunSummary),
        total: dto.total,
      };
    },
  });
}

/**
 * Hook to get a single run by ID.
 * Returns ViewModel (RunDetail).
 */
export function useRunDetail(runId: string) {
  return useQuery({
    queryKey: runKeys.detail(runId),
    queryFn: async () => {
      const dto = await getRun(runId);
      return mapRunDetail(dto);
    },
    enabled: !!runId,
  });
}

/**
 * Hook to get events for a run.
 * Returns ViewModel (RunEvent[]).
 */
export function useRunEvents(runId: string) {
  return useQuery({
    queryKey: runKeys.events(runId),
    queryFn: async () => {
      const dto = await getRunEvents(runId);
      return {
        items: dto.items.map(mapRunEvent),
      };
    },
    enabled: !!runId,
  });
}

/**
 * Hook to get the trace for a run.
 * Fetches trace by runId and maps to AgentExecutionTrace for use with AgentTraceView.
 */
export function useRunTrace(runId: string) {
  return useQuery({
    queryKey: runKeys.trace(runId),
    queryFn: async () => {
      const detail = await getTraceByRun(runId);
      return mapTraceToAgentExecution(detail);
    },
    enabled: !!runId,
  });
}

/**
 * Hook to get cost breakdown for a run.
 * Returns ViewModel (RunCostSummary).
 */
export function useRunCost(runId: string) {
  return useQuery({
    queryKey: runKeys.cost(runId),
    queryFn: async () => {
      const dto = await getRunCost(runId);
      return mapRunCost(dto);
    },
    enabled: !!runId,
  });
}

/**
 * Hook to get evaluation results for a run.
 * Returns ViewModel (RunEvaluationSummary).
 */
export function useRunEvaluation(runId: string) {
  return useQuery({
    queryKey: runKeys.evaluation(runId),
    queryFn: async () => {
      const dto = await getRunEvaluation(runId);
      return mapRunEvaluation(dto);
    },
    enabled: !!runId,
  });
}

/**
 * Hook to replay a run — re-execute with the same input.
 */
export function useReplayRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (runId: string) => {
      const dto = await replayRun(runId);
      return mapRunDetail(dto);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: runKeys.lists() });
    },
  });
}
