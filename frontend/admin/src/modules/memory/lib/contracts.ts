export type MemoryTypeStr = 'episodic' | 'semantic' | 'procedural';

export interface MemoryItemData {
  id: number;
  userId: string;
  sessionId: string | null;
  memoryType: MemoryTypeStr;
  content: string;
  summary: string | null;
  relevanceScore: number;
  accessCount: number;
  isActive: boolean;
  createdAtUtc: string;
  updatedAtUtc: string;
}

export interface MemoryStatsData {
  userId: string;
  countsByType: Partial<Record<MemoryTypeStr, number>>;
  totalActive: number;
}

export type PagedResult<T> = {
  items: T[];
  totalCount: number;
  page: number;
  pageSize: number;
};
