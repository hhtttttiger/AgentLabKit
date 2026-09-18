import { apiRequest } from '@/shared/api/client';
import type { DatasetData, CaseData } from '../../lib/contracts';

export function listDatasets() {
  return apiRequest<{ items: DatasetData[]; total: number }>('/api/eval/datasets');
}

export function createDataset(body: { name: string; description?: string; tags?: string[] }) {
  return apiRequest<DatasetData>('/api/eval/datasets', { method: 'POST', body });
}

export function deleteDataset(id: string) {
  return apiRequest<void>(`/api/eval/datasets/${id}`, { method: 'DELETE' });
}

export function listCases(datasetId: string) {
  return apiRequest<CaseData[]>(`/api/eval/datasets/${datasetId}/cases`);
}

export function createCases(datasetId: string, cases: Array<{ inputText: string; expectedOutput?: string; context?: string[] }>) {
  return apiRequest<{ added: number; total: number }>(`/api/eval/datasets/${datasetId}/cases`, { method: 'POST', body: cases });
}

export function deleteCase(datasetId: string, caseId: string) {
  return apiRequest<void>(`/api/eval/datasets/${datasetId}/cases/${caseId}`, { method: 'DELETE' });
}

export interface DesktopAgentData {
  id: string;
  displayName: string;
  kind: 'native' | 'external' | string;
  availability: 'ready' | 'not_installed' | string;
  version: string | null;
  message: string | null;
}

export function listDesktopAgents() {
  return apiRequest<DesktopAgentData[]>('/api/desktop/agents');
}

export function replayCase(body: { sourceRunId: string; agentId: string; workingDirectory: string }) {
  return apiRequest<{ runId: string; status: string; targetKey: string; metadata: Record<string, unknown> }>('/api/desktop/replay', { method: 'POST', body });
}
