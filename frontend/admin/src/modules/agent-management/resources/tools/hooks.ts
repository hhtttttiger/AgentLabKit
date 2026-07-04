import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getErrorMessage } from '@/shared/api/errors';
import { agentManagementQueryKeys } from '../../lib/queryKeys';
import {
  createToolDefinition,
  createVersionToolBinding,
  deleteVersionToolBinding,
  disableToolDefinition,
  getToolDefinition,
  listToolDefinitions,
  listVersionToolBindings,
  syncBuiltinTools,
  updateVersionToolBinding,
  updateToolDefinition,
} from './api';
import type {
  CreateToolDefinitionRequest,
  ToolListQuery,
  UpdateToolDefinitionRequest,
} from './types';

function translateToolError(message: string): string {
  if (message.includes('tool_definition_duplicate')) return '该工具名称已存在。';
  if (message.includes('tool_definition_not_found')) return '未找到该工具定义。';
  if (message.includes('tool_definition_not_active')) return '选择的工具未启用或不存在。';
  if (message.includes('tool_definition_builtin_immutable')) return '内置工具不可手动编辑，由 Python 运行时自动同步。';
  if (message.includes('tool_definition_has_active_bindings')) return '该工具已被 Agent 版本绑定，无法禁用。';
  if (message.includes('agent_runtime_catalog_unreachable')) return '无法连接 Python Agent Runtime，请确认服务已启动。';
  if (message.includes('agent_runtime_catalog_timeout')) return '读取 Python Agent Runtime 工具目录超时。';
  if (message.includes('agent_runtime_catalog_fetch_failed')) return '读取 Python Agent Runtime 工具目录失败。';
  if (message.includes('concurrency_conflict')) return '数据已被其他用户修改，请刷新后重试。';
  return message;
}

export function useToolDefinitionList(query: ToolListQuery) {
  return useQuery({
    queryKey: agentManagementQueryKeys.tools('list', query),
    queryFn: async () => {
      const result = await listToolDefinitions(query);
      return result.items;
    },
  });
}

export function useToolDefinition(toolName: string) {
  return useQuery({
    queryKey: agentManagementQueryKeys.tools('detail', toolName),
    queryFn: () => getToolDefinition(toolName),
    enabled: !!toolName,
  });
}

export function useVersionToolBindings(agentKey: string, versionNumber: number | null) {
  return useQuery({
    queryKey: agentManagementQueryKeys.tools('version-bindings', { agentKey, versionNumber }),
    queryFn: () => listVersionToolBindings(agentKey, versionNumber!),
    enabled: !!agentKey && versionNumber !== null,
  });
}

export function useToolDefinitionMutations() {
  const queryClient = useQueryClient();

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: agentManagementQueryKeys.toolsRoot() });

  const create = useMutation({
    mutationFn: (model: CreateToolDefinitionRequest) => createToolDefinition(model),
    onSuccess: invalidate,
  });

  const update = useMutation({
    mutationFn: ({ toolName, model }: { toolName: string; model: UpdateToolDefinitionRequest }) =>
      updateToolDefinition(toolName, model),
    onSuccess: invalidate,
  });

  const disable = useMutation({
    mutationFn: (toolName: string) => disableToolDefinition(toolName),
    onSuccess: invalidate,
  });

  const sync = useMutation({
    mutationFn: () => syncBuiltinTools(),
    onSuccess: invalidate,
  });

  return {
    create,
    update,
    disable,
    sync,
    getMutationMessage(error: unknown) {
      return translateToolError(getErrorMessage(error));
    },
  };
}

export {
  createVersionToolBinding,
  updateVersionToolBinding,
  deleteVersionToolBinding,
};
