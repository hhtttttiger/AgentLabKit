import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { switchTestLanguage } from '@/shared/test/setup';
import { KnowledgeBaseListPage } from './KnowledgeBaseListPage';

vi.mock('../resources/knowledge-base/hooks', () => ({
  useKbList: () => ({
    data: { items: [], totalCount: 0 },
    isLoading: false,
    isFetching: false,
    refetch: vi.fn(),
  }),
  useKbMutations: () => ({
    create: { isPending: false, mutate: vi.fn() },
    update: { isPending: false, mutate: vi.fn() },
    remove: { isPending: false, mutate: vi.fn() },
  }),
}));

describe('KnowledgeBaseListPage', () => {
  it('renders English toolbar and empty state copy', async () => {
    await switchTestLanguage('en-US');

    render(
      <MemoryRouter>
        <KnowledgeBaseListPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole('heading', { name: 'Knowledge base' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Create knowledge base' })).toBeInTheDocument();
    expect(screen.getByLabelText('Search')).toBeInTheDocument();
    expect(screen.getByLabelText('Status')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Refresh' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reset' })).toBeInTheDocument();
    expect(screen.getByText('No knowledge bases')).toBeInTheDocument();
  });
});
