import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { costAnalysisQueryKeys } from '../../lib/queryKeys';
import { listAlerts, acknowledgeAlert, evaluateAlerts } from './api';

export function useAlertList(acknowledged?: boolean | null) {
  return useQuery({
    queryKey: costAnalysisQueryKeys.alerts(acknowledged),
    queryFn: () => listAlerts(acknowledged),
    staleTime: 15_000,
  });
}

export function useAcknowledgeAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: acknowledgeAlert,
    onSuccess: () => qc.invalidateQueries({ queryKey: costAnalysisQueryKeys.alerts() }),
  });
}

export function useEvaluateAlerts() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: evaluateAlerts,
    onSuccess: () => qc.invalidateQueries({ queryKey: costAnalysisQueryKeys.alerts() }),
  });
}
