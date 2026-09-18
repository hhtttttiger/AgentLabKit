import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { switchTestLanguage } from '@/shared/test/setup';
import { NewSessionPage } from './NewSessionPage';

vi.mock('@/modules/ai-chat/hooks', () => ({
  useChatAgentOptions: () => ({
    data: [
      { id: 'local-agent', name: 'Native Agent', type: 'agent', agentKind: 'native' },
      { id: 'codex', name: 'Codex', type: 'agent', agentKind: 'external' },
    ],
    isLoading: false,
  }),
}));

vi.mock('@/modules/ai-chat/api', () => ({
  streamAgentChatMessage: vi.fn(),
}));

vi.mock('@/modules/overview/lib/workspace', () => ({
  loadLocalProject: () => null,
  pickLocalProject: vi.fn(),
  saveLocalProject: vi.fn(),
}));

vi.mock('@/modules/settings/api', () => ({
  getDesktopModelSettings: vi.fn(),
}));

vi.mock('@/shared/runtime/config', () => ({
  isLocalDesktopMode: () => false,
}));

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <NewSessionPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('NewSessionPage', () => {
  it('offers only interactive Native Agent executors', async () => {
    await switchTestLanguage('en-US');
    renderPage();

    expect(screen.getByRole('option', { name: 'Native Agent' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Codex' })).not.toBeInTheDocument();
  });
});
