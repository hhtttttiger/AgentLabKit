import { apiRequest } from '@/shared/api/client';
import type { PagedResult } from '@/shared/types/paging';
import type {
  CreateSkillDefinitionApiRequest,
  SkillBindingApiRequest,
  SkillBindingApiView,
  SkillDefinitionApiView,
  SkillListQuery,
  UpdateSkillDefinitionApiRequest,
} from './types';

export function listSkills(query: SkillListQuery) {
  return apiRequest<PagedResult<SkillDefinitionApiView>>('/api/agent-skills/definitions', { query });
}

export function getSkill(skillKey: string) {
  return apiRequest<SkillDefinitionApiView>(`/api/agent-skills/definitions/${encodeURIComponent(skillKey)}`);
}

export function createSkill(model: CreateSkillDefinitionApiRequest) {
  return apiRequest<SkillDefinitionApiView>('/api/agent-skills/definitions', {
    method: 'POST',
    body: model,
  });
}

export function updateSkill(skillKey: string, model: UpdateSkillDefinitionApiRequest) {
  return apiRequest<SkillDefinitionApiView>(`/api/agent-skills/definitions/${encodeURIComponent(skillKey)}`, {
    method: 'PUT',
    body: model,
  });
}

export function publishSkill(skillKey: string) {
  return apiRequest<SkillDefinitionApiView>(`/api/agent-skills/definitions/${encodeURIComponent(skillKey)}/publish`, {
    method: 'POST',
  });
}

export function deleteSkill(skillKey: string) {
  return apiRequest<void>(`/api/agent-skills/definitions/${encodeURIComponent(skillKey)}`, {
    method: 'DELETE',
  });
}

export function listVersionSkillBindings(agentKey: string, versionNumber: number) {
  return apiRequest<SkillBindingApiView[]>(
    `/api/agents/${encodeURIComponent(agentKey)}/versions/${versionNumber}/skill-bindings`,
  );
}

export function createVersionSkillBinding(agentKey: string, versionNumber: number, model: SkillBindingApiRequest) {
  return apiRequest<SkillBindingApiView>(
    `/api/agents/${encodeURIComponent(agentKey)}/versions/${versionNumber}/skill-bindings`,
    {
      method: 'POST',
      body: model,
    },
  );
}

export function updateVersionSkillBinding(agentKey: string, versionNumber: number, skillKey: string, model: Omit<SkillBindingApiRequest, 'skillKey'>) {
  return apiRequest<SkillBindingApiView>(
    `/api/agents/${encodeURIComponent(agentKey)}/versions/${versionNumber}/skill-bindings/${encodeURIComponent(skillKey)}`,
    {
      method: 'PUT',
      body: model,
    },
  );
}

export function deleteVersionSkillBinding(agentKey: string, versionNumber: number, skillKey: string) {
  return apiRequest<void>(
    `/api/agents/${encodeURIComponent(agentKey)}/versions/${versionNumber}/skill-bindings/${encodeURIComponent(skillKey)}`,
    { method: 'DELETE' },
  );
}
