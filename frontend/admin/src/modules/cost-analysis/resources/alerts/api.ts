import { apiRequest } from '@/shared/api/client';
import type { AlertData } from '../../lib/contracts';

export function listAlerts(acknowledged?: boolean | null, limit = 50) {
  const query: Record<string, string | number | boolean> = { limit };
  if (acknowledged != null) query.acknowledged = acknowledged;
  return apiRequest<AlertData[]>('/api/cost/alerts', { query });
}

export function acknowledgeAlert(alertId: string) {
  return apiRequest<void>(`/api/cost/alerts/${alertId}/acknowledge`, { method: 'POST' });
}

export function evaluateAlerts() {
  return apiRequest<{ triggeredCount: number }>('/api/cost/alerts/evaluate', { method: 'POST' });
}
