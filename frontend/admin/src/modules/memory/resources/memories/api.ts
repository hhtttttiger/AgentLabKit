import { apiRequest } from '@/shared/api/client';
import type { MemoryItemData, MemoryStatsData, PagedResult } from '../../lib/contracts';

const API_PREFIX = '/api/memories';

export interface ListMemoriesParams {
  memoryType?: string;
  page?: number;
  pageSize?: number;
  signal?: AbortSignal;
}

export function listMemories(params: ListMemoriesParams) {
  const { signal, ...query } = params;
  return apiRequest<PagedResult<MemoryItemData>>(API_PREFIX, { query, signal });
}

export function getMemoryStats(signal?: AbortSignal) {
  return apiRequest<MemoryStatsData>(`${API_PREFIX}/stats`, { signal });
}

export function deactivateMemory(memoryId: number) {
  return apiRequest<void>(`${API_PREFIX}/${memoryId}`, { method: 'PATCH' });
}

export function deleteMemory(memoryId: number) {
  return apiRequest<void>(`${API_PREFIX}/${memoryId}`, { method: 'DELETE' });
}

export function searchMemories(body: {
  query: string;
  memoryTypes?: string[];
  topK?: number;
  signal?: AbortSignal;
}) {
  const { signal, ...rest } = body;
  return apiRequest<MemoryItemData[]>(`${API_PREFIX}/search`, { method: 'POST', body: rest, signal });
}

export function consolidateMemories(body: {
  memoryType?: string;
  batchSize?: number;
}) {
  return apiRequest<{ consolidatedCount: number }>(`${API_PREFIX}/consolidate`, { method: 'POST', body });
}
