import { apiRequest } from '@/shared/api/client';
import type {
  AgentDetailView,
  AgentListQuery,
  AgentSummaryView,
  CreateAgentRequest,
  DisableAgentRequest,
  PublishAgentRequest,
  UpdateAgentRequest,
} from '../../lib/contracts';
import type { PagedResult } from '@/shared/types/paging';

export function listAgents(query: AgentListQuery) {
  return apiRequest<PagedResult<AgentSummaryView>>('/api/agents', { query });
}

export function getAgent(agentKey: string) {
  return apiRequest<AgentDetailView>(`/api/agents/${agentKey}`);
}

export function createAgent(model: CreateAgentRequest) {
  return apiRequest<AgentDetailView>('/api/agents', { method: 'POST', body: model });
}

export function updateAgent(agentKey: string, model: UpdateAgentRequest) {
  return apiRequest<AgentDetailView>(`/api/agents/${agentKey}`, { method: 'PUT', body: model });
}

export function publishAgent(agentKey: string, model: PublishAgentRequest) {
  return apiRequest<AgentDetailView>(`/api/agents/${agentKey}/publish`, { method: 'POST', body: model });
}

export function disableAgent(agentKey: string, model: DisableAgentRequest) {
  return apiRequest<AgentDetailView>(`/api/agents/${agentKey}/disable`, { method: 'POST', body: model });
}
