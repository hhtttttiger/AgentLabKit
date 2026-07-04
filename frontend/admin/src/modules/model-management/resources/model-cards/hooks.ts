import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { getErrorMessage } from '@/shared/api/errors';
import type { LlmModelFeatureWriteModel, LlmModelListQuery, LlmModelWriteModel } from '../../lib/contracts';
import { translateCatalogError } from '../../lib/errors';
import { modelManagementQueryKeys, modelManagementStaleTime } from '../../lib/queryKeys';
import { createModel, deleteModel, deleteModelFeature, getModel, listModels, updateModel, upsertModelFeature } from './api';

export function useModelList(query: LlmModelListQuery) {
  return useQuery({
    queryKey: modelManagementQueryKeys.models('list', query),
    queryFn: () => listModels(query),
    staleTime: modelManagementStaleTime.list,
  });
}

export function useModelDetail(modelKey: string | undefined) {
  return useQuery({
    queryKey: modelManagementQueryKeys.models('detail', modelKey),
    queryFn: () => getModel(modelKey!),
    staleTime: modelManagementStaleTime.detail,
    enabled: Boolean(modelKey),
  });
}

export function useModelMutations(options?: { onCreated?: (modelKey: string) => void }) {
  const queryClient = useQueryClient();
  const { t } = useTranslation();

  const invalidate = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ['model-management', 'models'], refetchType: 'active' }),
      queryClient.invalidateQueries({ queryKey: ['model-management', 'model-instances'], refetchType: 'active' }),
      queryClient.invalidateQueries({ queryKey: ['model-management', 'model-bindings'], refetchType: 'active' }),
      queryClient.invalidateQueries({ queryKey: ['model-management', 'options'], refetchType: 'active' }),
    ]);

  const create = useMutation({
    mutationFn: (model: LlmModelWriteModel) => createModel(model),
    onSuccess: (result) => {
      invalidate();
      if (options?.onCreated) {
        options.onCreated(result.modelKey);
      }
    },
  });

  const update = useMutation({
    mutationFn: ({ modelKey, model }: { modelKey: string; model: LlmModelWriteModel }) => updateModel(modelKey, model),
    onSuccess: invalidate,
  });

  const remove = useMutation({
    mutationFn: (modelKey: string) => deleteModel(modelKey),
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

export function useModelFeatureMutations() {
  const queryClient = useQueryClient();
  const { t } = useTranslation();

  const invalidate = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ['model-management', 'models'], refetchType: 'active' }),
      queryClient.invalidateQueries({ queryKey: ['model-management', 'model-instances'], refetchType: 'active' }),
      queryClient.invalidateQueries({ queryKey: ['model-management', 'options'], refetchType: 'active' }),
    ]);

  const upsert = useMutation({
    mutationFn: ({
      modelKey,
      featureKey,
      model,
    }: {
      modelKey: string;
      featureKey: string;
      model: LlmModelFeatureWriteModel;
    }) => upsertModelFeature(modelKey, featureKey, model),
    onSuccess: invalidate,
  });

  const remove = useMutation({
    mutationFn: ({ modelKey, featureKey }: { modelKey: string; featureKey: string }) => deleteModelFeature(modelKey, featureKey),
    onSuccess: invalidate,
  });

  return {
    upsert,
    remove,
    getMutationMessage(error: unknown) {
      return t(translateCatalogError(getErrorMessage(error)));
    },
  };
}
