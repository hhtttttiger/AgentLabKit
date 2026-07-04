import { useQuery } from '@tanstack/react-query';
import { kbQueryKeys } from '../knowledge-base/queryKeys';
import * as api from './api';

export function useTopRecalledDocuments(kbId: string, limit = 100) {
  return useQuery({
    queryKey: kbQueryKeys.topRecalled(kbId, limit),
    queryFn: () => api.listTopRecalledDocuments(kbId, limit),
    enabled: Boolean(kbId),
  });
}
