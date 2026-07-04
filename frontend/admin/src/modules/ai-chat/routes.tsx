/**
 * AI Chat Module - Routes
 */

import { type RouteObject } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { lazyRoute, routeElement } from '@/app/route-lazy';
import { useChatAgentOptions, useChatModelOptions } from './hooks';

const AiChatLayout = lazyRoute(() => import('./pages/AiChatLayout'), 'AiChatLayout');
const AiChatPage = lazyRoute(() => import('./pages/AiChatPage'), 'AiChatPage');

function AiChatPageLoader() {
  const { t } = useTranslation();
  const { data: agentOptions = [], isLoading: isLoadingAgents } = useChatAgentOptions();
  const { data: modelOptions = [], isLoading } = useChatModelOptions();

  if (isLoading || isLoadingAgents) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-text-muted">{t('modules.aiChat.loading')}</div>
      </div>
    );
  }

  return (
    <AiChatPage
      agentOptions={agentOptions}
      modelOptions={modelOptions}
    />
  );
}

export const aiChatRoutes: RouteObject[] = [
  {
    path: 'ai-chat',
    element: routeElement(AiChatLayout),
    children: [
      {
        index: true,
        element: routeElement(AiChatPageLoader),
      },
    ],
  },
];
