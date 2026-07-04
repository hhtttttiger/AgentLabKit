export const kbQueryKeys = {
  all: () => ['knowledge-base'] as const,
  lists: () => ['knowledge-base', 'list'] as const,
  list: (filters: unknown) => ['knowledge-base', 'list', filters] as const,
  detail: (kbId: string | undefined) => ['knowledge-base', 'detail', kbId] as const,
  folders: (kbId: string) => ['knowledge-base', kbId, 'folders'] as const,
  documents: (kbId: string, filters?: unknown) => ['knowledge-base', kbId, 'documents', filters] as const,
  document: (kbId: string, docId: string) => ['knowledge-base', kbId, 'document', docId] as const,
  topRecalled: (kbId: string, limit: number) => ['knowledge-base', kbId, 'top-recalled', limit] as const,
  segments: (kbId: string, docId: string, filters?: unknown) => ['knowledge-base', kbId, docId, 'segments', filters] as const,
  processing: (kbId: string, docId: string) => ['knowledge-base', kbId, docId, 'processing'] as const,
  indexes: (kbId: string, docId: string) => ['knowledge-base', kbId, docId, 'indexes'] as const,
  search: (kbId: string, query: string, topK: number, searchMode: string) =>
    ['knowledge-base', kbId, 'search', query, topK, searchMode] as const,
};
