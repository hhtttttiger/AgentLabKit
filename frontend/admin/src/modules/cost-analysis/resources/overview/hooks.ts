import { useQuery } from '@tanstack/react-query';
import { costAnalysisQueryKeys } from '../../lib/queryKeys';
import { getCostOverview, getBreakdownByModel, getCostTrend } from './api';
import type { Granularity } from '../../lib/contracts';

export function useCostOverview(days = 30) {
  return useQuery({
    queryKey: costAnalysisQueryKeys.overview(days),
    queryFn: () => getCostOverview(days),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useBreakdownByModel(days = 30) {
  return useQuery({
    queryKey: costAnalysisQueryKeys.breakdownByModel(days),
    queryFn: () => getBreakdownByModel(days),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useCostTrend(granularity: Granularity = 'day', days = 30) {
  return useQuery({
    queryKey: costAnalysisQueryKeys.trend(granularity, days),
    queryFn: () => getCostTrend(granularity, days),
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });
}
