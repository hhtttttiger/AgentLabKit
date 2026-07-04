import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getErrorMessage } from '@/shared/api/errors';
import { agentManagementQueryKeys } from '../../lib/queryKeys';
import { translateAgentError } from '../../lib/errors';
import { createAgent, disableAgent, getAgent, listAgents, publishAgent, updateAgent } from './api';
import type {
  AgentListQuery,
  CreateAgentRequest,
  DisableAgentRequest,
  PublishAgentRequest,
  UpdateAgentRequest,
} from '../../lib/contracts';

export function useAgentList(query: AgentListQuery) {
  return useQuery({
    queryKey: agentManagementQueryKeys.agents('list', query),
    queryFn: () => listAgents(query),
  });
}

export function useAgent(agentKey: string) {
  return useQuery({
    queryKey: agentManagementQueryKeys.agents('detail', agentKey),
    queryFn: () => getAgent(agentKey),
    enabled: !!agentKey,
  });
}

export function useAgentMutations() {
  const queryClient = useQueryClient();

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: agentManagementQueryKeys.agentsRoot(),
    });

  const create = useMutation({
    mutationFn: (model: CreateAgentRequest) => createAgent(model),
    onSuccess: invalidate,
  });

  const update = useMutation({
    mutationFn: ({ agentKey, model }: { agentKey: string; model: UpdateAgentRequest }) =>
      updateAgent(agentKey, model),
    onSuccess: invalidate,
  });

  const publish = useMutation({
    mutationFn: ({ agentKey, model }: { agentKey: string; model: PublishAgentRequest }) =>
      publishAgent(agentKey, model),
    onSuccess: async (_, variables) => {
      await invalidate();
      // Also invalidate version list cache
      queryClient.invalidateQueries({
        queryKey: agentManagementQueryKeys.versionsRoot(variables.agentKey),
      });
    },
  });

  const disable = useMutation({
    mutationFn: ({ agentKey, model }: { agentKey: string; model: DisableAgentRequest }) =>
      disableAgent(agentKey, model),
    onSuccess: invalidate,
  });

  return {
    create,
    update,
    publish,
    disable,
    getMutationMessage(error: unknown) {
      return translateAgentError(getErrorMessage(error));
    },
  };
}
