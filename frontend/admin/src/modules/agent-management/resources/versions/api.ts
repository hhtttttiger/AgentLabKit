import { apiRequest } from '@/shared/api/client';
import type { PagedResult } from '@/shared/types/paging';
import type {
  AgentVersionSummaryView,
  CreateVersionRequest,
  UpdateVersionRequest,
  VersionDetailView,
} from '../../lib/contracts';

export function listVersions(agentKey: string, query: { page?: number; pageSize?: number } = {}) {
  return apiRequest<PagedResult<AgentVersionSummaryView>>(`/api/agents/${agentKey}/versions`, { query });
}

export function getVersionDetail(agentKey: string, versionNumber: number) {
  return apiRequest<VersionDetailView>(`/api/agents/${agentKey}/versions/${versionNumber}`);
}

export function createVersion(agentKey: string, model: CreateVersionRequest) {
  return apiRequest<VersionDetailView>(`/api/agents/${agentKey}/versions`, {
    method: 'POST',
    body: model,
  });
}

export function updateVersion(agentKey: string, versionNumber: number, model: UpdateVersionRequest) {
  return apiRequest<VersionDetailView>(`/api/agents/${agentKey}/versions/${versionNumber}`, {
    method: 'PUT',
    body: model,
  });
}
