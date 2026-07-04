import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { evaluationQueryKeys } from '../../lib/queryKeys';
import { listRunConfigs, createRunConfig, triggerRun, listRuns, getRunDetail } from './api';

export function useRunConfigList() {
  return useQuery({ queryKey: evaluationQueryKeys.configs(), queryFn: listRunConfigs });
}

export function useCreateRunConfig() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: createRunConfig, onSuccess: () => qc.invalidateQueries({ queryKey: evaluationQueryKeys.configs() }) });
}

export function useTriggerRun() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: triggerRun, onSuccess: () => qc.invalidateQueries({ queryKey: evaluationQueryKeys.runs() }) });
}

export function useRunList() {
  return useQuery({ queryKey: evaluationQueryKeys.runs(), queryFn: listRuns });
}

export function useRunDetail(runId: string) {
  return useQuery({ queryKey: evaluationQueryKeys.runDetail(runId), queryFn: () => getRunDetail(runId), enabled: !!runId });
}
