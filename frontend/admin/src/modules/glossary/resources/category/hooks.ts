import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as api from './api';
import { glossaryQueryKeys } from '../../lib/queryKeys';
import type {
  GlossaryCategoryCreateRequest,
  GlossaryCategoryListQuery,
  GlossaryCategoryUpdateRequest,
} from '../../lib/contracts';

export function useGlossaryCategories(filters: GlossaryCategoryListQuery = {}) {
  return useQuery({
    queryKey: glossaryQueryKeys.categories(filters),
    queryFn: () => api.listGlossaryCategories(filters),
  });
}

export function useGlossaryCategory(categoryId: string | undefined) {
  return useQuery({
    queryKey: ['glossary', 'category', categoryId] as const,
    queryFn: () => api.getGlossaryCategory(categoryId!),
    enabled: Boolean(categoryId),
  });
}

export function useGlossaryCategoryMutations() {
  const queryClient = useQueryClient();
  const invalidate = () => queryClient.invalidateQueries({ queryKey: glossaryQueryKeys.all() });

  const create = useMutation({
    mutationFn: (data: GlossaryCategoryCreateRequest) => api.createGlossaryCategory(data),
    onSuccess: invalidate,
  });

  const update = useMutation({
    mutationFn: ({ categoryId, data }: { categoryId: string; data: GlossaryCategoryUpdateRequest }) =>
      api.updateGlossaryCategory(categoryId, data),
    onSuccess: invalidate,
  });

  const remove = useMutation({
    mutationFn: (categoryId: string) => api.deleteGlossaryCategory(categoryId),
    onSuccess: invalidate,
  });

  return { create, update, remove };
}
