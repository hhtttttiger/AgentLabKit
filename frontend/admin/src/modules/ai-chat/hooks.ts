import { useQuery } from '@tanstack/react-query';
import { listChatAgentOptions, listChatModelOptions } from './api';

export function useChatModelOptions() {
  return useQuery({
    queryKey: ['ai-chat', 'model-options'],
    queryFn: listChatModelOptions,
  });
}

export function useChatAgentOptions() {
  return useQuery({
    queryKey: ['ai-chat', 'agent-options'],
    queryFn: listChatAgentOptions,
  });
}
