import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getErrorMessage } from '@/shared/api/errors';
import { agentManagementQueryKeys } from '../../lib/queryKeys';
import {
  createSkill,
  deleteSkill,
  getSkill,
  listSkills,
  publishSkill,
  updateSkill,
  listVersionSkillBindings,
} from './api';
import {
  mapSkillDefinition,
  type CreateSkillDefinitionApiRequest,
  type SkillListQuery,
  type UpdateSkillDefinitionApiRequest,
} from './types';

function translateSkillError(message: string): string {
  if (message.includes('skill_key_duplicate')) return '该技能标识已存在。';
  if (message.includes('skill_definition_not_found')) return '未找到该技能。';
  if (message.includes('skill_definition_already_published')) return '该技能已发布，无需重复发布。';
  if (message.includes('skill_definition_has_bindings')) return '该技能已被版本绑定，无法删除。';
  if (message.includes('skill_binding_duplicate')) return '该技能已绑定到当前版本。';
  if (message.includes('skill_definitions_not_published')) return '存在未发布技能，当前版本不可发布。';
  if (message.includes('concurrency_conflict')) return '数据已被其他用户修改，请刷新后重试。';
  return message;
}

export function useSkillList(query: SkillListQuery) {
  return useQuery({
    queryKey: agentManagementQueryKeys.skills('list', query),
    queryFn: async () => {
      const result = await listSkills(query);
      return result.items.map(mapSkillDefinition);
    },
  });
}

export function useSkill(skillKey: string) {
  return useQuery({
    queryKey: agentManagementQueryKeys.skills('detail', skillKey),
    queryFn: async () => mapSkillDefinition(await getSkill(skillKey)),
    enabled: !!skillKey,
  });
}

export function useVersionSkillBindings(agentKey: string, versionNumber: number | null) {
  return useQuery({
    queryKey: agentManagementQueryKeys.versions(agentKey, 'skill-bindings', versionNumber),
    queryFn: () => listVersionSkillBindings(agentKey, versionNumber!),
    enabled: !!agentKey && versionNumber !== null,
  });
}

export function useSkillMutations() {
  const queryClient = useQueryClient();

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: agentManagementQueryKeys.skillsRoot() });

  const create = useMutation({
    mutationFn: (model: CreateSkillDefinitionApiRequest) => createSkill(model),
    onSuccess: invalidate,
  });

  const update = useMutation({
    mutationFn: ({ skillKey, model }: { skillKey: string; model: UpdateSkillDefinitionApiRequest }) =>
      updateSkill(skillKey, model),
    onSuccess: invalidate,
  });

  const publish = useMutation({
    mutationFn: (skillKey: string) => publishSkill(skillKey),
    onSuccess: invalidate,
  });

  const remove = useMutation({
    mutationFn: (skillKey: string) => deleteSkill(skillKey),
    onSuccess: invalidate,
  });

  return {
    create,
    update,
    publish,
    remove,
    getMutationMessage(error: unknown) {
      return translateSkillError(getErrorMessage(error));
    },
  };
}
