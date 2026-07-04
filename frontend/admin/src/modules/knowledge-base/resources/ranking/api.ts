import { apiRequest } from '@/shared/api/client';
import type { TopRecalledKbDocumentView } from '../../lib/contracts';

export function listTopRecalledDocuments(kbId: string, limit = 100) {
  return apiRequest<TopRecalledKbDocumentView[]>(
    `/api/knowledge-bases/${kbId}/documents/top-recalled`,
    { query: { limit } },
  );
}
