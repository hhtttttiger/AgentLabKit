import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as api from './api';
import { glossaryQueryKeys } from '../../lib/queryKeys';
import type {
  GlossaryTermCreateRequest,
  GlossaryTermListQuery,
  GlossaryTermUpdateRequest,
} from '../../lib/contracts';

export function useGlossaryTerms(filters: GlossaryTermListQuery = {}) {
  return useQuery({
    queryKey: glossaryQueryKeys.terms(filters),
    queryFn: () => api.listGlossaryTerms(filters),
  });
}

export function useGlossaryTerm(termId: string | undefined) {
  return useQuery({
    queryKey: glossaryQueryKeys.term(termId),
    queryFn: () => api.getGlossaryTerm(termId!),
    enabled: Boolean(termId),
  });
}

export function useGlossaryTermMutations() {
  const queryClient = useQueryClient();
  const invalidate = () => queryClient.invalidateQueries({ queryKey: glossaryQueryKeys.all() });

  const create = useMutation({
    mutationFn: (data: GlossaryTermCreateRequest) => api.createGlossaryTerm(data),
    onSuccess: invalidate,
  });

  const update = useMutation({
    mutationFn: ({ termId, data }: { termId: string; data: GlossaryTermUpdateRequest }) =>
      api.updateGlossaryTerm(termId, data),
    onSuccess: invalidate,
  });

  const remove = useMutation({
    mutationFn: (termId: string) => api.deleteGlossaryTerm(termId),
    onSuccess: invalidate,
  });

  const importTerms = useMutation({
    mutationFn: (file: File) => api.importGlossaryTerms(file),
    onSuccess: invalidate,
  });

  return { create, update, remove, importTerms };
}
