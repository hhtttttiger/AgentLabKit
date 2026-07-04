import { useQuery } from '@tanstack/react-query';
import { getErrorMessage } from '@/shared/api/errors';
import { agentManagementQueryKeys } from '../../lib/queryKeys';
import { listVersionKnowledgeBaseBindings } from './api';

export function translateKnowledgeBaseBindingError(message: string): string {
  if (message.includes('knowledge_base_binding_not_found')) return '未找到该知识库绑定。';
  if (message.includes('knowledge_base_not_found')) return '未找到对应知识库。';
  if (message.includes('knowledge_base_not_active')) return '所选知识库不可绑定到当前版本。';
  if (message.includes('agent_version_not_draft')) return '已发布版本只读，请先创建草稿。';
  if (message.includes('concurrency_conflict')) return '数据已被其他用户修改，请刷新后重试。';
  return message;
}

export function getKnowledgeBaseBindingMutationMessage(error: unknown) {
  return translateKnowledgeBaseBindingError(getErrorMessage(error));
}

export function useVersionKnowledgeBaseBindings(agentKey: string, versionNumber: number | null) {
  return useQuery({
    queryKey: agentManagementQueryKeys.knowledgeBaseBindings(agentKey, 'list', versionNumber),
    queryFn: () => listVersionKnowledgeBaseBindings(agentKey, versionNumber!),
    enabled: !!agentKey && versionNumber !== null,
  });
}
