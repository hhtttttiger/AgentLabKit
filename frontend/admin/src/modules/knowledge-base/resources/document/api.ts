import { apiRequest } from '@/shared/api/client';
import type { KbDocumentView, KbQaCreateRequest, KbQaUpdateRequest, KbPagedResult, KbQaImportResult } from '../../lib/contracts';

export function listDocuments(kbId: string, query: { page?: number; pageSize?: number; source_type?: string; folder_id?: string }) {
  return apiRequest<KbPagedResult<KbDocumentView>>(`/api/knowledge-bases/${kbId}/documents`, { query });
}

export function getDocument(kbId: string, docId: string) {
  return apiRequest<KbDocumentView>(`/api/knowledge-bases/${kbId}/documents/${docId}`);
}

export function uploadDocument(kbId: string, file: File, folderId?: string | null) {
  const form = new FormData();
  form.append('file', file);
  if (folderId) {
    form.append('folderId', folderId);
  }
  return apiRequest<KbDocumentView>(`/api/knowledge-bases/${kbId}/documents/upload`, {
    method: 'POST',
    formBody: form,
  });
}

export function createQaPair(kbId: string, data: KbQaCreateRequest) {
  return apiRequest<KbDocumentView>(`/api/knowledge-bases/${kbId}/documents/qa`, {
    method: 'POST',
    body: data,
  });
}

export function updateQaPair(kbId: string, docId: string, data: KbQaUpdateRequest) {
  return apiRequest<KbDocumentView>(`/api/knowledge-bases/${kbId}/documents/${docId}`, {
    method: 'PUT',
    body: data,
  });
}

export function deleteDocument(kbId: string, docId: string) {
  return apiRequest<void>(`/api/knowledge-bases/${kbId}/documents/${docId}`, { method: 'DELETE' });
}

export function reindexDocument(kbId: string, docId: string) {
  return apiRequest<void>(`/api/knowledge-bases/${kbId}/documents/${docId}/reindex`, { method: 'POST' });
}

export function importQaPairs(kbId: string, file: File, folderId?: string | null) {
  const form = new FormData();
  form.append('file', file);
  if (folderId) {
    form.append('folderId', folderId);
  }
  return apiRequest<KbQaImportResult>(`/api/knowledge-bases/${kbId}/documents/qa/import`, {
    method: 'POST',
    formBody: form,
  });
}

export function moveDocument(kbId: string, docId: string, targetFolderId: string | null) {
  return apiRequest<void>(`/api/knowledge-bases/${kbId}/documents/${docId}/move`, {
    method: 'POST',
    body: { targetFolderId },
  });
}

export async function getProcessingStatus(kbId: string, docId: string) {
  const job = await apiRequest<import('../../lib/contracts').ProcessingJobView>(
    `/api/knowledge-bases/${kbId}/documents/${docId}/processing`,
  );
  if (job?.stageProgressJson) {
    try {
      (job as any).stageProgress = JSON.parse(job.stageProgressJson);
    } catch { /* ignore parse errors */ }
  }
  return job;
}

export function listDocumentIndexes(kbId: string, docId: string) {
  return apiRequest<import('../../lib/contracts').DocumentIndexView[]>(
    `/api/knowledge-bases/${kbId}/documents/${docId}/indexes`,
  );
}
