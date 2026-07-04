import { apiRequest } from '@/shared/api/client';
import type { PagedResult } from '@/shared/types/paging';
import type {
  CreateToolDefinitionRequest,
  ToolDefinitionApiView,
  ToolListQuery,
  UpdateToolDefinitionRequest,
  VersionToolBindingApiView,
} from './types';

export function listToolDefinitions(query: ToolListQuery) {
  return apiRequest<PagedResult<ToolDefinitionApiView>>('/api/agent-tools/definitions', { query });
}

export function getToolDefinition(toolName: string) {
  return apiRequest<ToolDefinitionApiView>(
    `/api/agent-tools/definitions/${encodeURIComponent(toolName)}`,
  );
}

export function createToolDefinition(model: CreateToolDefinitionRequest) {
  return apiRequest<ToolDefinitionApiView>('/api/agent-tools/definitions', {
    method: 'POST',
    body: model,
  });
}

export function updateToolDefinition(toolName: string, model: UpdateToolDefinitionRequest) {
  return apiRequest<ToolDefinitionApiView>(
    `/api/agent-tools/definitions/${encodeURIComponent(toolName)}`,
    { method: 'PUT', body: model },
  );
}

export function disableToolDefinition(toolName: string) {
  return apiRequest<void>(
    `/api/agent-tools/definitions/${encodeURIComponent(toolName)}/disable`,
    { method: 'POST' },
  );
}

export function syncBuiltinTools() {
  return apiRequest<{ synced: number }>('/api/agent-tools/definitions/sync', {
    method: 'POST',
    body: {},
  });
}

export function listVersionToolBindings(agentKey: string, versionNumber: number) {
  return apiRequest<VersionToolBindingApiView[]>(
    `/api/agents/${encodeURIComponent(agentKey)}/versions/${versionNumber}/tool-bindings`,
  );
}

export function createVersionToolBinding(
  agentKey: string,
  versionNumber: number,
  model: Omit<VersionToolBindingApiView, 'id' | 'createdAtUtc' | 'updatedAtUtc'>,
) {
  return apiRequest<VersionToolBindingApiView>(
    `/api/agents/${encodeURIComponent(agentKey)}/versions/${versionNumber}/tool-bindings`,
    {
      method: 'POST',
      body: model,
    },
  );
}

export function updateVersionToolBinding(
  agentKey: string,
  versionNumber: number,
  bindingId: string,
  model: Omit<VersionToolBindingApiView, 'id' | 'toolName' | 'createdAtUtc' | 'updatedAtUtc'>,
) {
  return apiRequest<VersionToolBindingApiView>(
    `/api/agents/${encodeURIComponent(agentKey)}/versions/${versionNumber}/tool-bindings/${encodeURIComponent(bindingId)}`,
    {
      method: 'PUT',
      body: model,
    },
  );
}

export function deleteVersionToolBinding(agentKey: string, versionNumber: number, bindingId: string) {
  return apiRequest<void>(
    `/api/agents/${encodeURIComponent(agentKey)}/versions/${versionNumber}/tool-bindings/${encodeURIComponent(bindingId)}`,
    { method: 'DELETE' },
  );
}
