import { apiRequest } from '@/shared/api/client';
import type {
  AuditListQuery,
  ExecutionAuditDetailView,
  ExecutionAuditView,
} from '../../lib/contracts';
import type { PagedResult } from '@/shared/types/paging';

export function listAudits(agentKey: string, query: AuditListQuery) {
  return apiRequest<PagedResult<ExecutionAuditView>>(`/api/agents/${agentKey}/audits`, { query });
}

export function getAuditDetail(agentKey: string, runId: string) {
  return apiRequest<ExecutionAuditDetailView>(`/api/agents/${agentKey}/audits/${runId}`);
}
