import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as api from './api';
import { kbQueryKeys } from '../knowledge-base/queryKeys';

const kbGlossaryBindingQueryKeys = {
  all: () => ['knowledge-base', 'glossary-binding'] as const,
  detail: (kbId: string | undefined) => ['knowledge-base', 'glossary-binding', kbId] as const,
};

export function useKbGlossaryBinding(kbId: string | undefined) {
  return useQuery({
    queryKey: kbGlossaryBindingQueryKeys.detail(kbId),
    queryFn: () => api.getKnowledgeBaseGlossaryBinding(kbId!),
    enabled: Boolean(kbId),
  });
}

export function useKbGlossaryBindingMutations() {
  const queryClient = useQueryClient();

  const replace = useMutation({
    mutationFn: api.replaceKnowledgeBaseGlossaryBinding,
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: kbGlossaryBindingQueryKeys.detail(variables.kbId) });
      queryClient.invalidateQueries({ queryKey: kbQueryKeys.detail(variables.kbId) });
    },
  });

  return { replace };
}
