import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { getErrorMessage } from '@/shared/api/errors';
import type { LlmModelInstanceListQuery, LlmModelInstanceWriteModel } from '../../lib/contracts';
import { translateCatalogError } from '../../lib/errors';
import { modelManagementQueryKeys, modelManagementStaleTime } from '../../lib/queryKeys';
import { createModelInstance, deleteModelInstance, listModelInstances, listModelInstancesByModel, updateModelInstance } from './api';

export function useModelInstanceList(query: LlmModelInstanceListQuery) {
  return useQuery({
    queryKey: modelManagementQueryKeys.modelInstances('list', query),
    queryFn: () => listModelInstances(query),
    staleTime: modelManagementStaleTime.list,
  });
}

export function useModelInstancesByModel(modelKey: string | null) {
  return useQuery({
    queryKey: modelManagementQueryKeys.modelInstances('by-model', modelKey),
    queryFn: () => listModelInstancesByModel(modelKey!),
    staleTime: modelManagementStaleTime.list,
    enabled: Boolean(modelKey),
  });
}

export function useModelInstanceMutations() {
  const queryClient = useQueryClient();
  const { t } = useTranslation(['common', 'modelManagement']);

  const invalidate = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ['model-management', 'model-instances'], refetchType: 'active' }),
      queryClient.invalidateQueries({ queryKey: ['model-management', 'models'], refetchType: 'active' }),
      queryClient.invalidateQueries({ queryKey: ['model-management', 'model-bindings'], refetchType: 'active' }),
      queryClient.invalidateQueries({ queryKey: ['model-management', 'options'], refetchType: 'active' }),
    ]);

  const create = useMutation({
    mutationFn: ({ modelKey, model }: { modelKey: string; model: LlmModelInstanceWriteModel }) => createModelInstance(modelKey, model),
    onSuccess: invalidate,
  });

  const update = useMutation({
    mutationFn: ({ instanceKey, model }: { instanceKey: string; model: LlmModelInstanceWriteModel }) => updateModelInstance(instanceKey, model),
    onSuccess: invalidate,
  });

  const remove = useMutation({
    mutationFn: (instanceKey: string) => deleteModelInstance(instanceKey),
    onSuccess: invalidate,
  });

  return {
    create,
    update,
    remove,
    getMutationMessage(error: unknown) {
      return t(translateCatalogError(getErrorMessage(error)));
    },
  };
}
