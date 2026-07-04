import { apiRequest } from '@/shared/api/client';
import type { KbSegmentView, KbPagedResult } from '../../lib/contracts';

export function listSegments(kbId: string, docId: string, query?: { page?: number; pageSize?: number }) {
  return apiRequest<KbPagedResult<KbSegmentView>>(
    `/api/knowledge-bases/${kbId}/documents/${docId}/segments`,
    { query },
  );
}

export function getSegment(kbId: string, docId: string, segId: string) {
  return apiRequest<KbSegmentView>(
    `/api/knowledge-bases/${kbId}/documents/${docId}/segments/${segId}`,
  );
}
