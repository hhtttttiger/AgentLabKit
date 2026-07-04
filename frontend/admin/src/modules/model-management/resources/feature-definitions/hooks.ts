import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { getErrorMessage } from '@/shared/api/errors';
import { modelManagementQueryKeys, modelManagementStaleTime } from '../../lib/queryKeys';
import { translateCatalogError } from '../../lib/errors';
import {
  createFeature,
  deleteFeature,
  listFeatures,
  updateFeature,
} from './api';
import type { LlmFeatureListQuery, LlmFeatureWriteModel } from '../../lib/contracts';

export function useFeatureList(query: LlmFeatureListQuery) {
  return useQuery({
    queryKey: modelManagementQueryKeys.features('list', query),
    queryFn: () => listFeatures(query),
    staleTime: modelManagementStaleTime.list,
  });
}

export function useFeatureMutations() {
  const queryClient = useQueryClient();
  const { t } = useTranslation();

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: ['model-management', 'features'],
      refetchType: 'active',
    });

  const create = useMutation({
    mutationFn: (model: LlmFeatureWriteModel) => createFeature(model),
    onSuccess: invalidate,
  });

  const update = useMutation({
    mutationFn: ({ featureKey, model }: { featureKey: string; model: LlmFeatureWriteModel }) =>
      updateFeature(featureKey, model),
    onSuccess: invalidate,
  });

  const remove = useMutation({
    mutationFn: (featureKey: string) => deleteFeature(featureKey),
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
