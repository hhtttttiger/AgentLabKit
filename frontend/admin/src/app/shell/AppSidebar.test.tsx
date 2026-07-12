import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import '@/styles/index.css';
import { ThemeProvider } from '@/shared/theme';
import { AppSidebar } from './AppSidebar';
import { switchTestLanguage } from '@/shared/test/setup';

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function renderSidebar(props: Partial<React.ComponentProps<typeof AppSidebar>> = {}) {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter>
        <ThemeProvider>
          <AppSidebar
            collapsed={false}
            onToggleCollapse={() => {}}
            displayName="Test User"
            onLogout={() => {}}
            {...props}
          />
        </ThemeProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('AppSidebar', () => {
  beforeEach(() => {
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
  });
  it('renders the ai chat navigation entry', () => {
    renderSidebar({ currentModuleKey: 'ai-chat' });

    expect(screen.getByRole('link', { name: 'AI 对话' })).toBeInTheDocument();
  });

  it('keeps the module nav scrollable when more entries are added', () => {
    renderSidebar({ currentModuleKey: 'model-management' });

    const nav = screen.getByRole('navigation', { name: '模块导航' });
    expect(getComputedStyle(nav).overflowY).toBe('auto');
  });

  it('renders English navigation labels after language switch', async () => {
    await switchTestLanguage('en-US');

    renderSidebar({ currentModuleKey: 'model-management' });

    expect(screen.getByRole('navigation', { name: 'Modules' })).toBeInTheDocument();
  });
});
