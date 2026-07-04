import type { DocumentSourceType } from '../../lib/contracts';

export type DocumentListFilters = {
  page: number;
  pageSize: number;
  type: DocumentSourceType | 'all';
  folderId?: string;
};

export const defaultDocumentListFilters: DocumentListFilters = {
  page: 1,
  pageSize: 20,
  type: 'all',
};

export function toDocumentListQuery(filters: DocumentListFilters) {
  return {
    page: filters.page,
    pageSize: filters.pageSize,
    source_type: filters.type === 'all' ? undefined : filters.type === 'File' ? 'file' : filters.type === 'QaPair' ? 'qa' : undefined,
    folder_id: filters.folderId,
  };
}
