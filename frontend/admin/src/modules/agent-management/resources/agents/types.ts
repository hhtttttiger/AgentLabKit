import type { AgentDetailView, AgentListQuery, AgentStatus, CreateAgentRequest } from '../../lib/contracts';

export type AgentFilters = {
  status: '' | AgentStatus;
  page: number;
  pageSize: number;
};

export const defaultAgentFilters: AgentFilters = {
  status: '',
  page: 1,
  pageSize: 10,
};

export const emptyAgentDraft: CreateAgentRequest = {
  agentKey: '',
  displayName: '',
  description: null,
  tags: [],
  metadata: {},
};

export function toAgentListQuery(filters: AgentFilters): AgentListQuery {
  return {
    status: filters.status || undefined,
    page: filters.page,
    pageSize: filters.pageSize,
  };
}

export function toAgentDraftFromDetail(detail: AgentDetailView): CreateAgentRequest {
  return {
    agentKey: detail.agentKey,
    displayName: detail.displayName,
    description: detail.description,
    tags: detail.tags,
    metadata: detail.metadata,
  };
}
