import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { memoryQueryKeys } from '../../lib/queryKeys';
import { listMemories, getMemoryStats, deactivateMemory, deleteMemory, consolidateMemories, searchMemories } from './api';

export function useMemoryList(params: {
  userId: string;
  memoryType?: string;
  page?: number;
  pageSize?: number;
}) {
  return useQuery({
    queryKey: memoryQueryKeys.list(params.userId, params.memoryType, params.page, params.pageSize),
    queryFn: ({ signal }) => listMemories({ memoryType: params.memoryType, page: params.page, pageSize: params.pageSize, signal }),
    enabled: params.userId !== '',
    staleTime: 5 * 60 * 1000,
  });
}

export function useMemoryStats(userId: string) {
  return useQuery({
    queryKey: memoryQueryKeys.stats(userId),
    queryFn: ({ signal }) => getMemoryStats(signal),
    enabled: userId !== '',
    staleTime: 30 * 1000,
  });
}

export function useDeactivateMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deactivateMemory,
    onSuccess: () => qc.invalidateQueries({ queryKey: memoryQueryKeys.all() }),
    onError: (error: Error) => {
      console.error('Failed to deactivate memory:', error);
    },
  });
}

export function useDeleteMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteMemory,
    onSuccess: () => qc.invalidateQueries({ queryKey: memoryQueryKeys.all() }),
    onError: (error: Error) => {
      console.error('Failed to delete memory:', error);
    },
  });
}

export function useConsolidateMemories() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: consolidateMemories,
    onSuccess: () => qc.invalidateQueries({ queryKey: memoryQueryKeys.all() }),
    onError: (error: Error) => {
      console.error('Failed to consolidate memories:', error);
    },
  });
}

export function useSearchMemories(params: {
  query: string;
  userId: string;
  memoryTypes?: string[];
  topK?: number;
}) {
  return useQuery({
    queryKey: memoryQueryKeys.search(params.userId, params.query, params.memoryTypes),
    queryFn: ({ signal }) => searchMemories({ query: params.query, memoryTypes: params.memoryTypes, topK: params.topK, signal }),
    enabled: params.userId !== '' && params.query.length > 0,
  });
}
