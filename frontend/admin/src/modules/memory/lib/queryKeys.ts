export const memoryQueryKeys = {
  all: () => ['memory'] as const,
  list: (userId: string, memoryType?: string, page?: number, pageSize?: number) =>
    ['memory', 'list', userId, memoryType ?? '', page ?? 1, pageSize ?? 20] as const,
  stats: (userId: string) => ['memory', 'stats', userId] as const,
  search: (userId: string, query: string, memoryTypes?: string[]) =>
    ['memory', 'search', userId, query, ...(memoryTypes ?? []).sort()] as const,
};
