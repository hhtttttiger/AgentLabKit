import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { getErrorMessage } from '@/shared/api/errors';
import { modelManagementQueryKeys, modelManagementStaleTime } from '../../lib/queryKeys';
import { translateCatalogError } from '../../lib/errors';
import { createConnectionProfile, deleteConnectionProfile, listConnectionProfiles, updateConnectionProfile } from './api';
import type { LlmConnectionProfileListQuery, LlmConnectionProfileWriteModel } from '../../lib/contracts';

export function useConnectionProfileList(query: LlmConnectionProfileListQuery) {
  return useQuery({
    queryKey: modelManagementQueryKeys.connectionProfiles('list', query),
    queryFn: () => listConnectionProfiles(query),
    staleTime: modelManagementStaleTime.list,
  });
}

export function useConnectionProfileMutations() {
  const queryClient = useQueryClient();
  const { t } = useTranslation(['common', 'modelManagement']);

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: ['model-management', 'connection-profiles'],
      refetchType: 'active',
    });

  const create = useMutation({
    mutationFn: (model: LlmConnectionProfileWriteModel) => createConnectionProfile(model),
    onSuccess: invalidate,
  });

  const update = useMutation({
    mutationFn: ({ profileKey, model }: { profileKey: string; model: LlmConnectionProfileWriteModel }) => updateConnectionProfile(profileKey, model),
    onSuccess: invalidate,
  });

  const remove = useMutation({
    mutationFn: (profileKey: string) => deleteConnectionProfile(profileKey),
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
