import { useQuery } from '@tanstack/react-query';
import { agentManagementQueryKeys } from '../../lib/queryKeys';
import { getAuditDetail, listAudits } from './api';
import type { AuditListQuery } from '../../lib/contracts';

export function useAuditList(agentKey: string, query: AuditListQuery) {
  return useQuery({
    queryKey: agentManagementQueryKeys.audits(agentKey, 'list', query),
    queryFn: () => listAudits(agentKey, query),
    enabled: !!agentKey,
  });
}

export function useAuditDetail(agentKey: string, runId: string | null) {
  return useQuery({
    queryKey: agentManagementQueryKeys.audits(agentKey, 'detail', runId),
    queryFn: () => getAuditDetail(agentKey, runId as string),
    enabled: !!agentKey && !!runId,
  });
}
