import { apiRequest } from '@/shared/api/client';
import type { CostOverviewData, CostBreakdownItem, CostTrendPoint, Granularity } from '../../lib/contracts';

export function getCostOverview(days = 30) {
  return apiRequest<CostOverviewData>('/api/cost/overview', { query: { days } });
}

export function getBreakdownByModel(days = 30, limit = 20) {
  return apiRequest<CostBreakdownItem[]>('/api/cost/breakdown/by-model', { query: { days, limit } });
}

export function getBreakdownByCapability(days = 30, limit = 20) {
  return apiRequest<CostBreakdownItem[]>('/api/cost/breakdown/by-capability', { query: { days, limit } });
}

export function getCostTrend(granularity: Granularity = 'day', days = 30) {
  return apiRequest<CostTrendPoint[]>('/api/cost/trend', { query: { granularity, days } });
}
