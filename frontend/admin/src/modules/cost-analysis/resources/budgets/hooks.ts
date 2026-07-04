import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { costAnalysisQueryKeys } from '../../lib/queryKeys';
import { listBudgets, createBudget, updateBudget, deleteBudget } from './api';

export function useBudgetList() {
  return useQuery({
    queryKey: costAnalysisQueryKeys.budgets(),
    queryFn: listBudgets,
    staleTime: 30_000,
  });
}

export function useCreateBudget() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createBudget,
    onSuccess: () => qc.invalidateQueries({ queryKey: costAnalysisQueryKeys.budgets() }),
  });
}

export function useUpdateBudget() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string; monthlyLimitUsd?: number; alertThresholdPct?: number; isEnabled?: boolean }) =>
      updateBudget(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: costAnalysisQueryKeys.budgets() }),
  });
}

export function useDeleteBudget() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteBudget,
    onSuccess: () => qc.invalidateQueries({ queryKey: costAnalysisQueryKeys.budgets() }),
  });
}
