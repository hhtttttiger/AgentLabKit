import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { switchTestLanguage } from '@/shared/test/setup';
import { GlossaryListPage } from './GlossaryListPage';

const categoryHookMocks = vi.hoisted(() => ({
  useGlossaryCategories: vi.fn(),
  useGlossaryCategoryMutations: vi.fn(),
}));

vi.mock('../resources/category/hooks', () => categoryHookMocks);

function createClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function mockCategoryMutations() {
  categoryHookMocks.useGlossaryCategoryMutations.mockReturnValue({
    create: { isPending: false, error: null, mutate: vi.fn(), reset: vi.fn() },
    update: { isPending: false, error: null, mutate: vi.fn(), reset: vi.fn() },
    remove: { isPending: false, error: null, mutate: vi.fn(), reset: vi.fn() },
  });
}

function renderPage() {
  const client = createClient();
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <GlossaryListPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('GlossaryListPage', () => {
  it('renders the glossary management shell with translated copy', async () => {
    await switchTestLanguage('en-US');
    categoryHookMocks.useGlossaryCategories.mockReturnValue({
      data: {
        items: [
          { id: 'cat-1', name: 'RAG', description: '检索增强生成', createdAtUtc: '2026-04-27T00:00:00Z', updatedAtUtc: null },
        ],
        page: 1,
        pageSize: 12,
        totalCount: 1,
      },
      isLoading: false,
      isError: false,
      isFetching: false,
      refetch: vi.fn(),
    });
    mockCategoryMutations();

    renderPage();

    expect(screen.getByRole('heading', { name: 'Glossary' })).toBeInTheDocument();
    expect(screen.getByText('Manage glossary categories and terms, then bind them to knowledge bases.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'New category' })).toBeInTheDocument();
    expect(screen.getByLabelText('Search')).toBeInTheDocument();
    expect(screen.getByText('RAG')).toBeInTheDocument();
  });

  it('shows a translated empty state when no categories are available', async () => {
    await switchTestLanguage('en-US');
    categoryHookMocks.useGlossaryCategories.mockReturnValue({
      data: {
        items: [],
        page: 1,
        pageSize: 12,
        totalCount: 0,
      },
      isLoading: false,
      isError: false,
      isFetching: false,
      refetch: vi.fn(),
    });
    mockCategoryMutations();

    renderPage();

    expect(screen.getByText('No glossary categories')).toBeInTheDocument();
    expect(screen.getByText('Click "New category" to get started.')).toBeInTheDocument();
  });

  it('resets the search keyword from the toolbar reset action', async () => {
    const user = userEvent.setup();
    await switchTestLanguage('en-US');

    categoryHookMocks.useGlossaryCategories.mockReturnValue({
      data: {
        items: [
          { id: 'cat-1', name: 'RAG', description: '检索增强生成', createdAtUtc: '2026-04-27T00:00:00Z', updatedAtUtc: null },
        ],
        page: 1,
        pageSize: 12,
        totalCount: 1,
      },
      isLoading: false,
      isError: false,
      isFetching: false,
      refetch: vi.fn(),
    });
    mockCategoryMutations();

    renderPage();

    const searchInput = screen.getByLabelText('Search');
    await user.type(searchInput, 'agent');
    expect(searchInput).toHaveValue('agent');

    await user.click(screen.getByRole('button', { name: 'Reset' }));
    expect(searchInput).toHaveValue('');
  });

  it('opens the create drawer from the page action', async () => {
    const user = userEvent.setup();
    await switchTestLanguage('en-US');

    categoryHookMocks.useGlossaryCategories.mockReturnValue({
      data: {
        items: [],
        page: 1,
        pageSize: 12,
        totalCount: 0,
      },
      isLoading: false,
      isError: false,
      isFetching: false,
      refetch: vi.fn(),
    });
    mockCategoryMutations();

    renderPage();

    // There are two "New category" buttons (header + empty state); click the first one
    const buttons = screen.getAllByRole('button', { name: 'New category' });
    await user.click(buttons[0]);

    expect(screen.getByRole('heading', { name: 'New category' })).toBeInTheDocument();
  });
});
