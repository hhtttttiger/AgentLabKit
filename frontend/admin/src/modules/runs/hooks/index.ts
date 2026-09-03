import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getTraceDetail } from '@/modules/observability/resources/traces/api';
import { captureRun, getRun, listRuns, replayRun } from '../api/client';
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

export function useRunList(options: RunFilters & { limit?: number; offset?: number } = {}) {
  const limit = options.limit ?? 20;
  const offset = options.offset ?? 0;

  return useQuery({
    queryKey: [...runKeys.all, 'list', limit, offset],
    queryFn: async () => {
      const result = await listRuns(limit, offset);
      return { ...result, items: result.items.map(mapRunDetail) };
    },
  });
}

/** These resources are not exposed under /api/runs in the sealed contract. */
export function useRunEvents(_runId: string) { return useQuery< { items: RunEvent[] } | null>({ queryKey: [...runKeys.all, 'events'], queryFn: async () => null, enabled: false }); }
export function useRunCost(_runId: string) { return useQuery<RunCostSummary | null>({ queryKey: [...runKeys.all, 'cost'], queryFn: async () => null, enabled: false }); }
export function useRunEvaluation(_runId: string) { return useQuery<RunEvaluationSummary | null>({ queryKey: [...runKeys.all, 'evaluation'], queryFn: async () => null, enabled: false }); }

export function useCaptureRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ runId, request }: { runId: string; request: import('../api/dto').CaptureRunRequest }) => captureRun(runId, request),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: runKeys.all }),
  });
}

export function useReplayRun() {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: async (runId: string) => mapRunDetail((await replayRun(runId)).run), onSuccess: () => { queryClient.invalidateQueries({ queryKey: runKeys.all }); } });
}
