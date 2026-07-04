import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getErrorMessage } from '@/shared/api/errors';
import { agentManagementQueryKeys } from '../../lib/queryKeys';
import {
  createMcpServer,
  deleteMcpServer,
  getMcpServer,
  listMcpServers,
  updateMcpServer,
  listVersionMcpBindings,
} from './api';
import {
  mapMcpServer,
  type CreateMcpServerApiRequest,
  type McpServerListQuery,
  type UpdateMcpServerApiRequest,
} from './types';

function translateMcpError(message: string): string {
  if (message.includes('mcp_server_config_name_duplicate')) return '该 MCP Server 名称已存在。';
  if (message.includes('mcp_server_config_not_found')) return '未找到该 MCP Server，可能已被删除。';
  if (message.includes('mcp_server_config_has_bindings')) return '该 MCP Server 已被版本绑定，无法删除。';
  if (message.includes('mcp_server_config_stdio_requires_command')) return 'stdio 类型必须填写 command。';
  if (message.includes('mcp_server_config_http_requires_url') || message.includes('mcp_server_config_sse_requires_url')) return 'http/sse 类型必须填写 URL。';
  if (message.includes('mcp_server_config_transport_mismatch')) return 'transport 与 config 内 transport 不一致。';
  if (message.includes('mcp_server_config_used_by_published_version')) return '该 MCP Server 已被已发布版本使用，当前不可修改。';
  if (message.includes('mcp_binding_reserved_override_key')) return 'configOverrides 不能覆盖 name 或 transport。';
  if (message.includes('concurrency_conflict')) return '数据已被其他用户修改，请刷新后重试。';
  return message;
}

export function useMcpServerList(query: McpServerListQuery) {
  return useQuery({
    queryKey: agentManagementQueryKeys.mcpServers('list', query),
    queryFn: async () => {
      const result = await listMcpServers(query);
      return result.items.map(mapMcpServer);
    },
  });
}

export function useMcpServer(name: string) {
  return useQuery({
    queryKey: agentManagementQueryKeys.mcpServers('detail', name),
    queryFn: async () => mapMcpServer(await getMcpServer(name)),
    enabled: !!name,
  });
}

export function useVersionMcpBindings(agentKey: string, versionNumber: number | null) {
  return useQuery({
    queryKey: agentManagementQueryKeys.versions(agentKey, 'mcp-bindings', versionNumber),
    queryFn: () => listVersionMcpBindings(agentKey, versionNumber!),
    enabled: !!agentKey && versionNumber !== null,
  });
}

export function useMcpServerMutations() {
  const queryClient = useQueryClient();

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: agentManagementQueryKeys.mcpServersRoot(),
    });

  const create = useMutation({
    mutationFn: (model: CreateMcpServerApiRequest) => createMcpServer(model),
    onSuccess: invalidate,
  });

  const update = useMutation({
    mutationFn: ({ name, model }: { name: string; model: UpdateMcpServerApiRequest }) =>
      updateMcpServer(name, model),
    onSuccess: invalidate,
  });

  const del = useMutation({
    mutationFn: (name: string) => deleteMcpServer(name),
    onSuccess: invalidate,
  });

  return {
    create,
    update,
    delete: del,
    getMutationMessage(error: unknown) {
      return translateMcpError(getErrorMessage(error));
    },
  };
}
