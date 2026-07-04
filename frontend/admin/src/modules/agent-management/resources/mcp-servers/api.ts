import { apiRequest } from '@/shared/api/client';
import type { PagedResult } from '@/shared/types/paging';
import type {
  CreateMcpServerApiRequest,
  McpBindingApiRequest,
  McpBindingApiView,
  McpServerApiView,
  McpServerListQuery,
  UpdateMcpServerApiRequest,
} from './types';

export function listMcpServers(query: McpServerListQuery) {
  return apiRequest<PagedResult<McpServerApiView>>('/api/agent-mcp/servers', {
    query: { page: query.page ?? 1, pageSize: query.pageSize ?? 200 },
  });
}

export function getMcpServer(name: string) {
  return apiRequest<McpServerApiView>(`/api/agent-mcp/servers/${encodeURIComponent(name)}`);
}

export function createMcpServer(model: CreateMcpServerApiRequest) {
  return apiRequest<McpServerApiView>('/api/agent-mcp/servers', {
    method: 'POST',
    body: model,
  });
}

export function updateMcpServer(name: string, model: UpdateMcpServerApiRequest) {
  return apiRequest<McpServerApiView>(`/api/agent-mcp/servers/${encodeURIComponent(name)}`, {
    method: 'PUT',
    body: model,
  });
}

export function deleteMcpServer(name: string) {
  return apiRequest<void>(`/api/agent-mcp/servers/${encodeURIComponent(name)}`, { method: 'DELETE' });
}

export function listVersionMcpBindings(agentKey: string, versionNumber: number) {
  return apiRequest<McpBindingApiView[]>(
    `/api/agents/${encodeURIComponent(agentKey)}/versions/${versionNumber}/mcp-bindings`,
  );
}

export function createVersionMcpBinding(agentKey: string, versionNumber: number, model: McpBindingApiRequest) {
  return apiRequest<McpBindingApiView>(
    `/api/agents/${encodeURIComponent(agentKey)}/versions/${versionNumber}/mcp-bindings`,
    {
      method: 'POST',
      body: model,
    },
  );
}

export function updateVersionMcpBinding(agentKey: string, versionNumber: number, serverName: string, model: Omit<McpBindingApiRequest, 'serverName'>) {
  return apiRequest<McpBindingApiView>(
    `/api/agents/${encodeURIComponent(agentKey)}/versions/${versionNumber}/mcp-bindings/${encodeURIComponent(serverName)}`,
    {
      method: 'PUT',
      body: model,
    },
  );
}

export function deleteVersionMcpBinding(agentKey: string, versionNumber: number, serverName: string) {
  return apiRequest<void>(
    `/api/agents/${encodeURIComponent(agentKey)}/versions/${versionNumber}/mcp-bindings/${encodeURIComponent(serverName)}`,
    { method: 'DELETE' },
  );
}
