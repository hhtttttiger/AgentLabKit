import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as api from './api';
import { kbQueryKeys } from './queryKeys';
import type { KbCreateRequest, KbUpdateRequest } from '../../lib/contracts';
import type { KbListFilters } from './types';
import { toKbListQuery } from './types';

export function useKbList(filters: KbListFilters) {
  const query = toKbListQuery(filters);
  return useQuery({
    queryKey: kbQueryKeys.list(query),
    queryFn: () => api.listKnowledgeBases(query),
  });
}

export function useKbDetail(kbId: string | undefined) {
  return useQuery({
    queryKey: kbQueryKeys.detail(kbId),
    queryFn: () => api.getKnowledgeBase(kbId!),
    enabled: Boolean(kbId),
  });
}

export function useKbMutations(options?: { onCreated?: (id: string) => void }) {
  const queryClient = useQueryClient();
  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: kbQueryKeys.all() });

  const create = useMutation({
    mutationFn: (data: KbCreateRequest) => api.createKnowledgeBase(data),
    onSuccess: (result) => {
      invalidate();
      options?.onCreated?.(result.id);
    },
  });

  const update = useMutation({
    mutationFn: ({ kbId, data }: { kbId: string; data: KbUpdateRequest }) =>
      api.updateKnowledgeBase(kbId, data),
    onSuccess: invalidate,
  });

  const remove = useMutation({
    mutationFn: (kbId: string) => api.deleteKnowledgeBase(kbId),
    onSuccess: invalidate,
  });

  return { create, update, remove };
}
