import { useRef } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as api from './api';
import { kbQueryKeys } from '../knowledge-base/queryKeys';
import type { KbQaCreateRequest, KbQaUpdateRequest } from '../../lib/contracts';
import type { DocumentListFilters } from './types';
import { toDocumentListQuery } from './types';

const POLL_INTERVALS = [3000, 6000, 12000, 30000, 60000];

export function useDocumentList(kbId: string, filters: DocumentListFilters) {
  const query = toDocumentListQuery(filters);
  const backoffIndexRef = useRef(0);

  return useQuery({
    queryKey: kbQueryKeys.documents(kbId, query),
    queryFn: () => api.listDocuments(kbId, query),
    refetchInterval: (queryResult) => {
      const items = queryResult.state.data?.items;
      if (!items) return false;
      const processing = items.some(
        (d) => d.ingestStatus === 'Pending' || d.ingestStatus === 'Processing',
      );
      if (!processing) {
        backoffIndexRef.current = 0;
        return false;
      }
      const interval = POLL_INTERVALS[backoffIndexRef.current] ?? POLL_INTERVALS[POLL_INTERVALS.length - 1];
      backoffIndexRef.current = Math.min(backoffIndexRef.current + 1, POLL_INTERVALS.length - 1);
      return interval;
    },
  });
}

export function useProcessingStatus(kbId: string, docId: string, poll = false) {
  const backoffIndexRef = useRef(0);

  return useQuery({
    queryKey: kbQueryKeys.processing(kbId, docId),
    queryFn: () => api.getProcessingStatus(kbId, docId),
    enabled: !!docId,
    refetchInterval: poll
      ? (queryResult) => {
          const status = queryResult.state.data?.currentStage;
          if (!status || status === 'Completed' || status === 'Failed') {
            backoffIndexRef.current = 0;
            return false;
          }
          const interval = POLL_INTERVALS[backoffIndexRef.current] ?? POLL_INTERVALS[POLL_INTERVALS.length - 1];
          backoffIndexRef.current = Math.min(backoffIndexRef.current + 1, POLL_INTERVALS.length - 1);
          return interval;
        }
      : false,
  });
}

export function useDocumentDetail(kbId: string, docId: string) {
  return useQuery({
    queryKey: kbQueryKeys.document(kbId, docId),
    queryFn: () => api.getDocument(kbId, docId),
    enabled: !!docId,
  });
}

export function useDocumentIndexes(kbId: string, docId: string) {
  return useQuery({
    queryKey: kbQueryKeys.indexes(kbId, docId),
    queryFn: () => api.listDocumentIndexes(kbId, docId),
    enabled: !!docId,
  });
}

export function useDocumentMutations(kbId: string) {
  const queryClient = useQueryClient();
  const invalidateDocs = () =>
    queryClient.invalidateQueries({ queryKey: ['knowledge-base', kbId, 'documents'] });

  const upload = useMutation({
    mutationFn: ({ file, folderId }: { file: File; folderId?: string | null }) => api.uploadDocument(kbId, file, folderId),
    onSuccess: invalidateDocs,
  });

  const createQa = useMutation({
    mutationFn: (data: KbQaCreateRequest) => api.createQaPair(kbId, data),
    onSuccess: invalidateDocs,
  });

  const updateQa = useMutation({
    mutationFn: ({ docId, data }: { docId: string; data: KbQaUpdateRequest }) =>
      api.updateQaPair(kbId, docId, data),
    onSuccess: invalidateDocs,
  });

  const remove = useMutation({
    mutationFn: (docId: string) => api.deleteDocument(kbId, docId),
    onSuccess: invalidateDocs,
  });

  const reindex = useMutation({
    mutationFn: (docId: string) => api.reindexDocument(kbId, docId),
    onSuccess: invalidateDocs,
  });

  const importQa = useMutation({
    mutationFn: ({ file, folderId }: { file: File; folderId?: string | null }) => api.importQaPairs(kbId, file, folderId),
    onSuccess: invalidateDocs,
  });

  const moveDoc = useMutation({
    mutationFn: ({ docId, targetFolderId }: { docId: string; targetFolderId: string | null }) =>
      api.moveDocument(kbId, docId, targetFolderId),
    onSuccess: invalidateDocs,
  });

  return { upload, createQa, updateQa, remove, reindex, importQa, moveDoc };
}
