import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { switchTestLanguage } from '@/shared/test/setup';
import { CategoryTermsTab } from './CategoryTermsTab';

const hookMocks = vi.hoisted(() => ({
  useGlossaryCategories: vi.fn(),
  useGlossaryTerms: vi.fn(),
  useGlossaryTermMutations: vi.fn(),
}));

vi.mock('../../resources/category/hooks', () => ({
  useGlossaryCategories: hookMocks.useGlossaryCategories,
}));

vi.mock('../../resources/term/hooks', () => ({
  useGlossaryTerms: hookMocks.useGlossaryTerms,
  useGlossaryTermMutations: hookMocks.useGlossaryTermMutations,
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useParams: () => ({ categoryId: 'cat-1' }),
  };
});

function renderTab() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <CategoryTermsTab />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('CategoryTermsTab', () => {
  it('renders translated toolbar and empty state', async () => {
    await switchTestLanguage('en-US');

    hookMocks.useGlossaryCategories.mockReturnValue({
      data: { items: [] },
      isLoading: false,
    });
    hookMocks.useGlossaryTerms.mockReturnValue({
      data: { items: [], totalCount: 0 },
      isLoading: false,
      isFetching: false,
      isError: false,
      refetch: vi.fn(),
    });
    hookMocks.useGlossaryTermMutations.mockReturnValue({
      create: { isPending: false, error: null, mutate: vi.fn(), reset: vi.fn() },
      update: { isPending: false, error: null, mutate: vi.fn(), reset: vi.fn() },
      remove: { isPending: false, error: null, mutate: vi.fn(), reset: vi.fn() },
      importTerms: { isPending: false, error: null, mutate: vi.fn(), reset: vi.fn() },
    });

    renderTab();

    expect(screen.getByRole('button', { name: 'Import terms' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'New term' })).toBeInTheDocument();
    expect(screen.getByLabelText('Search')).toBeInTheDocument();
    expect(screen.getByText('No terms')).toBeInTheDocument();
    expect(screen.getByText('There are no terms in this category yet. Add one manually or import a file.')).toBeInTheDocument();
  });
});
