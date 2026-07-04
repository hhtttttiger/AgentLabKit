import { apiRequest } from '@/shared/api/client';
import type {
  CreateVersionKnowledgeBaseBindingRequest,
  UpdateVersionKnowledgeBaseBindingRequest,
  VersionKnowledgeBaseBindingApiView,
} from './types';

export function listVersionKnowledgeBaseBindings(agentKey: string, versionNumber: number) {
  return apiRequest<VersionKnowledgeBaseBindingApiView[]>(
    `/api/agents/${encodeURIComponent(agentKey)}/versions/${versionNumber}/knowledge-base-bindings`,
  );
}

export function createVersionKnowledgeBaseBinding(
  agentKey: string,
  versionNumber: number,
  model: CreateVersionKnowledgeBaseBindingRequest,
) {
  return apiRequest<VersionKnowledgeBaseBindingApiView>(
    `/api/agents/${encodeURIComponent(agentKey)}/versions/${versionNumber}/knowledge-base-bindings`,
    {
      method: 'POST',
      body: model,
    },
  );
}

export function updateVersionKnowledgeBaseBinding(
  agentKey: string,
  versionNumber: number,
  bindingId: string,
  model: UpdateVersionKnowledgeBaseBindingRequest,
) {
  return apiRequest<VersionKnowledgeBaseBindingApiView>(
    `/api/agents/${encodeURIComponent(agentKey)}/versions/${versionNumber}/knowledge-base-bindings/${encodeURIComponent(bindingId)}`,
    {
      method: 'PUT',
      body: model,
    },
  );
}

export function deleteVersionKnowledgeBaseBinding(
  agentKey: string,
  versionNumber: number,
  bindingId: string,
) {
  return apiRequest<void>(
    `/api/agents/${encodeURIComponent(agentKey)}/versions/${versionNumber}/knowledge-base-bindings/${encodeURIComponent(bindingId)}`,
    {
      method: 'DELETE',
    },
  );
}
