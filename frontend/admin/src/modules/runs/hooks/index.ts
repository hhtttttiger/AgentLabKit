import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getTraceDetail } from '@/modules/observability/resources/traces/api';
import { getRun, replayRun } from '../api/client';
import { mapRunDetail } from '../mappers/runMapper';
import { mapTraceToAgentExecution } from '../mappers/traceMapper';
import type { RunCostSummary, RunDetail, RunEvaluationSummary, RunEvent, RunFilters } from '../types';

export const runKeys = { all: ['runs'] as const, detail: (id: string) => [...runKeys.all, id] as const, trace: (id: string) => [...runKeys.all, 'trace', id] as const };

export function useRunDetail(runId: string) {
  return useQuery({ queryKey: runKeys.detail(runId), queryFn: async (): Promise<RunDetail> => mapRunDetail(await getRun(runId)), enabled: !!runId });
}

export function useRunTrace(traceId: string | null) {
  return useQuery({ queryKey: runKeys.trace(traceId ?? ''), queryFn: async () => mapTraceToAgentExecution(await getTraceDetail(traceId as string)), enabled: !!traceId });
}

/** No Runtime Run list endpoint is public in Adapter v1; keep list UI explicitly deferred. */
export function useRunList(_filters?: RunFilters) {
  return useQuery<{ items: import('../types').RunSummary[]; total: number }>({
    queryKey: [...runKeys.all, 'list'], queryFn: async () => ({ items: [], total: 0 }), enabled: false,
  });
}

/** These resources are not exposed under /api/runs in the sealed contract. */
export function useRunEvents(_runId: string) { return useQuery< { items: RunEvent[] } | null>({ queryKey: [...runKeys.all, 'events'], queryFn: async () => null, enabled: false }); }
export function useRunCost(_runId: string) { return useQuery<RunCostSummary | null>({ queryKey: [...runKeys.all, 'cost'], queryFn: async () => null, enabled: false }); }
export function useRunEvaluation(_runId: string) { return useQuery<RunEvaluationSummary | null>({ queryKey: [...runKeys.all, 'evaluation'], queryFn: async () => null, enabled: false }); }

export function useReplayRun() {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: async (runId: string) => mapRunDetail((await replayRun(runId)).run), onSuccess: () => { queryClient.invalidateQueries({ queryKey: runKeys.all }); } });
}
