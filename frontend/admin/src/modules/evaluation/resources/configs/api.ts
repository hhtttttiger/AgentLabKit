import { apiRequest } from '@/shared/api/client';
import type { RunConfigData, RunData, RunDetailData } from '../../lib/contracts';

export function listRunConfigs() {
  return apiRequest<RunConfigData[]>('/api/eval/run-configs');
}

export function createRunConfig(body: { name: string; datasetId: string; targetType?: string; targetKey?: string; metricConfigs?: Record<string, unknown>[]; judgeModelBindingKey?: string }) {
  return apiRequest<RunConfigData>('/api/eval/run-configs', { method: 'POST', body });
}

export function triggerRun(configId: string) {
  return apiRequest<RunData>(`/api/eval/run-configs/${configId}/run`, { method: 'POST' });
}

export function listRuns() {
  return apiRequest<RunData[]>('/api/eval/runs');
}

export function getRunDetail(runId: string) {
  return apiRequest<RunDetailData>(`/api/eval/runs/${runId}`);
}
