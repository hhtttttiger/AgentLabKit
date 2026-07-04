import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getErrorMessage } from '@/shared/api/errors';
import { agentManagementQueryKeys } from '../../lib/queryKeys';
import { translateAgentError } from '../../lib/errors';
import { createVersion, listVersions, getVersionDetail, updateVersion } from './api';
import type { CreateVersionRequest, UpdateVersionRequest } from '../../lib/contracts';

export function useVersionList(agentKey: string, query?: { page?: number; pageSize?: number }) {
  return useQuery({
    queryKey: agentManagementQueryKeys.versions(agentKey, 'list', query),
    queryFn: () => listVersions(agentKey, query ?? {}),
    enabled: !!agentKey,
  });
}

export function useVersionDetail(agentKey: string, versionNumber: number | null) {
  return useQuery({
    queryKey: agentManagementQueryKeys.versions(agentKey, 'detail', versionNumber),
    queryFn: () => getVersionDetail(agentKey, versionNumber!),
    enabled: !!agentKey && versionNumber !== null,
  });
}

export function useVersionMutations(agentKey: string) {
  const queryClient = useQueryClient();

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: agentManagementQueryKeys.versionsRoot(agentKey),
    });

  const create = useMutation({
    mutationFn: (model: CreateVersionRequest) => createVersion(agentKey, model),
    onSuccess: invalidate,
  });

  const update = useMutation({
    mutationFn: (params: { versionNumber: number; model: UpdateVersionRequest }) =>
      updateVersion(agentKey, params.versionNumber, params.model),
    onSuccess: invalidate,
  });

  return {
    create,
    update,
    getMutationMessage(error: unknown) {
      return translateAgentError(getErrorMessage(error));
    },
  };
}
