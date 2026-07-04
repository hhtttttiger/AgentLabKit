import { apiRequest } from '@/shared/api/client';
import type {
  KbFolderCreateRequest,
  KbFolderMoveRequest,
  KbFolderUpdateRequest,
  KbFolderView,
} from '../../lib/contracts';

export function listFolders(kbId: string) {
  return apiRequest<KbFolderView[]>(`/api/knowledge-bases/${kbId}/folders`);
}

export function createFolder(kbId: string, data: KbFolderCreateRequest) {
  return apiRequest<KbFolderView>(`/api/knowledge-bases/${kbId}/folders`, {
    method: 'POST',
    body: data,
  });
}

export function updateFolder(kbId: string, folderId: string, data: KbFolderUpdateRequest) {
  return apiRequest<KbFolderView>(`/api/knowledge-bases/${kbId}/folders/${folderId}`, {
    method: 'PATCH',
    body: data,
  });
}

export function deleteFolder(kbId: string, folderId: string) {
  return apiRequest<void>(`/api/knowledge-bases/${kbId}/folders/${folderId}`, { method: 'DELETE' });
}

export function moveFolder(kbId: string, folderId: string, data: KbFolderMoveRequest) {
  return apiRequest<void>(`/api/knowledge-bases/${kbId}/folders/${folderId}/move`, {
    method: 'POST',
    body: data,
  });
}
