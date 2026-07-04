import { useQuery } from '@tanstack/react-query';
import * as api from './api';
import { kbQueryKeys } from '../knowledge-base/queryKeys';
import type { SegmentListFilters } from './types';

export function useSegmentList(kbId: string, docId: string, filters: SegmentListFilters) {
  return useQuery({
    queryKey: kbQueryKeys.segments(kbId, docId, filters),
    queryFn: () => api.listSegments(kbId, docId, filters),
  });
}

export function useSegmentDetail(kbId: string, docId: string, segId: string) {
  return useQuery({
    queryKey: kbQueryKeys.segments(kbId, docId, { segId }),
    queryFn: () => api.getSegment(kbId, docId, segId),
    enabled: !!segId,
  });
}
