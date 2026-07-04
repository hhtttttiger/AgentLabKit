import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { evaluationQueryKeys } from '../../lib/queryKeys';
import { listDatasets, createDataset, deleteDataset, listCases, createCases, deleteCase } from './api';

export function useDatasetList() {
  return useQuery({ queryKey: evaluationQueryKeys.datasets(), queryFn: listDatasets });
}

export function useCreateDataset() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: createDataset, onSuccess: () => qc.invalidateQueries({ queryKey: evaluationQueryKeys.datasets() }) });
}

export function useDeleteDataset() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: deleteDataset, onSuccess: () => qc.invalidateQueries({ queryKey: evaluationQueryKeys.datasets() }) });
}

export function useCaseList(datasetId: string) {
  return useQuery({ queryKey: evaluationQueryKeys.cases(datasetId), queryFn: () => listCases(datasetId), enabled: !!datasetId });
}

export function useCreateCases(datasetId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cases: Array<{ inputText: string; expectedOutput?: string; context?: string[] }>) =>
      createCases(datasetId, cases),
    onSuccess: () => qc.invalidateQueries({ queryKey: evaluationQueryKeys.cases(datasetId) }),
  });
}

export function useDeleteCase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ datasetId, caseId }: { datasetId: string; caseId: string }) =>
      deleteCase(datasetId, caseId),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: evaluationQueryKeys.cases(variables.datasetId) });
    },
  });
}
