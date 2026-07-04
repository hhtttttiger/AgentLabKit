import { apiRequest } from '@/shared/api/client';
import type { KbSearchRequest, KbSearchResponse } from '../../lib/contracts';

export function searchKnowledgeBase(kbId: string, request: KbSearchRequest) {
  return apiRequest<KbSearchResponse>(`/api/knowledge-bases/${kbId}/search`, {
    method: 'POST',
    body: request,
  });
}
