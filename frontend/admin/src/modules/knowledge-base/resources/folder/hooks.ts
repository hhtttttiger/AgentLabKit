import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as api from './api';
import { kbQueryKeys } from '../knowledge-base/queryKeys';
import type {
  KbFolderCreateRequest,
  KbFolderMoveRequest,
  KbFolderUpdateRequest,
} from '../../lib/contracts';

export function useFolderList(kbId: string) {
  return useQuery({
    queryKey: kbQueryKeys.folders(kbId),
    queryFn: () => api.listFolders(kbId),
    enabled: !!kbId,
  });
}

export function useFolderMutations(kbId: string) {
  const queryClient = useQueryClient();
  const invalidateFolders = () => queryClient.invalidateQueries({ queryKey: kbQueryKeys.folders(kbId) });

  const create = useMutation({
    mutationFn: (data: KbFolderCreateRequest) => api.createFolder(kbId, data),
    onSuccess: invalidateFolders,
  });

  const update = useMutation({
    mutationFn: ({ folderId, data }: { folderId: string; data: KbFolderUpdateRequest }) =>
      api.updateFolder(kbId, folderId, data),
    onSuccess: invalidateFolders,
  });

  const remove = useMutation({
    mutationFn: (folderId: string) => api.deleteFolder(kbId, folderId),
    onSuccess: invalidateFolders,
  });

  const move = useMutation({
    mutationFn: ({ folderId, data }: { folderId: string; data: KbFolderMoveRequest }) =>
      api.moveFolder(kbId, folderId, data),
    onSuccess: invalidateFolders,
  });

  return { create, update, remove, move };
}
