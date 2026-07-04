import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { KbGlossaryTab } from './KbGlossaryTab';

const bindingHookMocks = vi.hoisted(() => ({
  useKbGlossaryBinding: vi.fn(),
  useKbGlossaryBindingMutations: vi.fn(),
}));

vi.mock('../../resources/glossary-binding/hooks', () => bindingHookMocks);

function renderPage() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/knowledge-base/kb-1/glossary']}>
        <Routes>
          <Route path="/knowledge-base/:kbId/glossary" element={<KbGlossaryTab />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('KbGlossaryTab', () => {
  it('renders glossary binding cards with checkbox selection', () => {
    bindingHookMocks.useKbGlossaryBinding.mockReturnValue({
      data: {
        knowledgeBaseId: 'kb-1',
        categoryIds: ['cat-1'],
        categories: [
          { id: 'cat-1', name: 'RAG', description: '检索增强生成', createdAtUtc: '2026-04-27T00:00:00Z', updatedAtUtc: null },
          { id: 'cat-2', name: 'Agent', description: 'Agent 术语', createdAtUtc: '2026-04-27T00:00:00Z', updatedAtUtc: null },
        ],
      },
      isLoading: false,
      isError: false,
      error: null,
    });
    bindingHookMocks.useKbGlossaryBindingMutations.mockReturnValue({
      replace: { isPending: false, mutate: vi.fn(), reset: vi.fn(), error: null },
    });

    renderPage();

    expect(screen.getByRole('heading', { name: '术语绑定' })).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: 'RAG' })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: 'Agent' })).not.toBeChecked();
    expect(screen.getByRole('button', { name: '保存绑定' })).toBeDisabled();
  });

  it('updates selected category ids and submits them in category order', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn();

    bindingHookMocks.useKbGlossaryBinding.mockReturnValue({
      data: {
        knowledgeBaseId: 'kb-1',
        categoryIds: ['cat-1'],
        categories: [
          { id: 'cat-1', name: 'RAG', description: '检索增强生成', createdAtUtc: '2026-04-27T00:00:00Z', updatedAtUtc: null },
          { id: 'cat-2', name: 'Agent', description: 'Agent 术语', createdAtUtc: '2026-04-27T00:00:00Z', updatedAtUtc: null },
        ],
      },
      isLoading: false,
      isError: false,
      error: null,
    });
    bindingHookMocks.useKbGlossaryBindingMutations.mockReturnValue({
      replace: { isPending: false, mutate, reset: vi.fn(), error: null },
    });

    renderPage();

    await user.click(screen.getByRole('checkbox', { name: 'Agent' }));
    await user.click(screen.getByRole('button', { name: '保存绑定' }));

    expect(mutate).toHaveBeenCalledWith({ kbId: 'kb-1', categoryIds: ['cat-1', 'cat-2'] });
  });

  it('shows category descriptions inline on each binding card', () => {
    bindingHookMocks.useKbGlossaryBinding.mockReturnValue({
      data: {
        knowledgeBaseId: 'kb-1',
        categoryIds: [],
        categories: [
          { id: 'cat-2', name: 'Agent', description: 'Agent 术语', createdAtUtc: '2026-04-27T00:00:00Z', updatedAtUtc: null },
        ],
      },
      isLoading: false,
      isError: false,
      error: null,
    });
    bindingHookMocks.useKbGlossaryBindingMutations.mockReturnValue({
      replace: { isPending: false, mutate: vi.fn(), reset: vi.fn(), error: null },
    });

    renderPage();

    expect(screen.getByText('Agent')).toBeInTheDocument();
    expect(screen.getByText('Agent 术语')).toBeInTheDocument();
  });

  it('renders a stable empty state when there are no glossary categories', () => {
    bindingHookMocks.useKbGlossaryBinding.mockReturnValue({
      data: {
        knowledgeBaseId: 'kb-1',
        categoryIds: [],
        categories: [],
      },
      isLoading: false,
      isError: false,
      error: null,
    });
    bindingHookMocks.useKbGlossaryBindingMutations.mockReturnValue({
      replace: { isPending: false, mutate: vi.fn(), reset: vi.fn(), error: null },
    });

    renderPage();

    expect(screen.getByText('暂无术语分类')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '保存绑定' })).not.toBeInTheDocument();
  });

  it('shows a reload warning instead of a generic load error when refresh fails after data exists', () => {
    const queryState = {
      data: {
        knowledgeBaseId: 'kb-1',
        categoryIds: ['cat-1'],
        categories: [
          { id: 'cat-1', name: 'RAG', description: '检索增强生成', createdAtUtc: '2026-04-27T00:00:00Z', updatedAtUtc: null },
        ],
      },
      isLoading: false,
      isError: true,
      error: new Error('刷新失败'),
    };

    bindingHookMocks.useKbGlossaryBinding.mockImplementation(() => queryState);
    bindingHookMocks.useKbGlossaryBindingMutations.mockReturnValue({
      replace: { isPending: false, mutate: vi.fn(), reset: vi.fn(), error: null },
    });

    renderPage();

    expect(screen.getByText('最新状态刷新失败，当前显示的是已加载结果。')).toBeInTheDocument();
    expect(screen.queryByText('刷新失败')).not.toBeInTheDocument();
  });
});
