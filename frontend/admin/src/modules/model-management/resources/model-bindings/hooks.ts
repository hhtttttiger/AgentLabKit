import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { getErrorMessage } from '@/shared/api/errors';
import type { LlmModelBindingListQuery, LlmModelBindingWriteModel } from '../../lib/contracts';
import { translateCatalogError } from '../../lib/errors';
import { modelManagementQueryKeys, modelManagementStaleTime } from '../../lib/queryKeys';
import { createModelBinding, deleteModelBinding, listModelBindings, updateModelBinding } from './api';

export function useModelBindingList(query: LlmModelBindingListQuery) {
  return useQuery({
    queryKey: modelManagementQueryKeys.modelBindings('list', query),
    queryFn: () => listModelBindings(query),
    staleTime: modelManagementStaleTime.list,
  });
}

export function useModelBindingMutations() {
  const queryClient = useQueryClient();
  const { t } = useTranslation();

  const invalidate = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ['model-management', 'model-bindings'], refetchType: 'active' }),
      queryClient.invalidateQueries({ queryKey: ['model-management', 'models'], refetchType: 'active' }),
      queryClient.invalidateQueries({ queryKey: ['model-management', 'options'], refetchType: 'active' }),
    ]);

  const create = useMutation({
    mutationFn: (model: LlmModelBindingWriteModel) => createModelBinding(model),
    onSuccess: invalidate,
  });

  const update = useMutation({
    mutationFn: ({ bindingKey, model }: { bindingKey: string; model: LlmModelBindingWriteModel }) => updateModelBinding(bindingKey, model),
    onSuccess: invalidate,
  });

  const remove = useMutation({
    mutationFn: (bindingKey: string) => deleteModelBinding(bindingKey),
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
