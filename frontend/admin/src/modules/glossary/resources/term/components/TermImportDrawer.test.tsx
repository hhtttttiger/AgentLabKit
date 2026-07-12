import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { PropsWithChildren } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { switchTestLanguage } from '@/shared/test/setup';
import { useGlossaryCategories, useGlossaryCategoryMutations } from '../../category/hooks';
import { useGlossaryTerm, useGlossaryTermMutations, useGlossaryTerms } from '../hooks';
import { glossaryQueryKeys } from '../../../lib/queryKeys';
import { TermImportDrawer } from './TermImportDrawer';

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function QueryWrapper({ client, children }: PropsWithChildren<{ client: QueryClient }>) {
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

function GlossaryListHarness() {
  const categories = useGlossaryCategories({ page: 2, pageSize: 5, search: 'RAG' });
  const terms = useGlossaryTerms({ categoryId: 'cat-1', page: 1, pageSize: 10, search: 'emb' });
  const term = useGlossaryTerm('term-1');

  return (
    <div>
      <span>{categories.data?.items[0]?.name}</span>
      <span>{terms.data?.items[0]?.term}</span>
      <span>{term.data?.term}</span>
    </div>
  );
}

function GlossaryMutationHarness() {
  const categoryMutations = useGlossaryCategoryMutations();
  const termMutations = useGlossaryTermMutations();

  return (
    <div>
      <button onClick={() => categoryMutations.create.mutate({ name: 'RAG', description: 'desc' })}>create-category</button>
      <button onClick={() => categoryMutations.update.mutate({ categoryId: 'cat-1', data: { name: 'Agent', description: 'updated' } })}>update-category</button>
      <button onClick={() => categoryMutations.remove.mutate('cat-1')}>delete-category</button>
      <button onClick={() => termMutations.create.mutate({ categoryId: 'cat-1', term: 'Embedding', synonyms: ['向量化'] })}>create-term</button>
      <button onClick={() => termMutations.update.mutate({ termId: 'term-1', data: { term: 'Retriever', synonyms: ['检索器'] } })}>update-term</button>
      <button onClick={() => termMutations.remove.mutate('term-1')}>delete-term</button>
      <button onClick={() => termMutations.importTerms.mutate(new File(['term,category'], 'terms.csv', { type: 'text/csv' }))}>import-terms</button>
    </div>
  );
}

describe('glossary data layer', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('builds stable glossary query keys for categories, terms and kb bindings', () => {
    expect(glossaryQueryKeys.categories({ page: 1, search: 'rag' })).toEqual(['glossary', 'categories', { page: 1, search: 'rag' }]);
    expect(glossaryQueryKeys.terms({ categoryId: 'cat-1', page: 2 })).toEqual(['glossary', 'terms', { categoryId: 'cat-1', page: 2 }]);
    expect(glossaryQueryKeys.term('term-1')).toEqual(['glossary', 'term', 'term-1']);
    expect(glossaryQueryKeys.kbBindings('kb-1')).toEqual(['glossary', 'kb-bindings', 'kb-1']);
  });

  it('loads glossary categories and terms through the shared api client', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;

      if (url.includes('/api/glossary/categories?page=2&pageSize=5&search=RAG')) {
        return new Response(JSON.stringify({
          success: true,
          msg: 'ok',
          data: {
            items: [{ id: 'cat-1', name: 'RAG', description: 'desc', createdAtUtc: '2026-04-27T00:00:00Z', updatedAtUtc: null }],
            page: 2,
            pageSize: 5,
            totalCount: 1,
          },
        }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }

      if (url.includes('/api/glossary/terms?categoryId=cat-1&page=1&pageSize=10&search=emb')) {
        return new Response(JSON.stringify({
          success: true,
          msg: 'ok',
          data: {
            items: [{ id: 'term-1', categoryId: 'cat-1', term: 'Embedding', synonyms: ['向量化'], createdAtUtc: '2026-04-27T00:00:00Z', updatedAtUtc: null }],
            page: 1,
            pageSize: 10,
            totalCount: 1,
          },
        }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }

      if (url.endsWith('/api/glossary/terms/term-1')) {
        return new Response(JSON.stringify({
          success: true,
          msg: 'ok',
          data: { id: 'term-1', categoryId: 'cat-1', term: 'Embedding', synonyms: ['向量化'], createdAtUtc: '2026-04-27T00:00:00Z', updatedAtUtc: null },
        }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }

      throw new Error(`Unexpected fetch: ${url}`);
    });

    const client = createQueryClient();
    render(<GlossaryListHarness />, { wrapper: ({ children }) => <QueryWrapper client={client}>{children}</QueryWrapper> });

    expect(await screen.findByText('RAG')).toBeInTheDocument();
    expect(screen.getAllByText('Embedding')).toHaveLength(2);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it('invalidates glossary cache after category and term mutations succeed', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
      const method = init?.method ?? 'GET';

      if (method === 'POST' && url.endsWith('/api/glossary/categories')) {
        return new Response(JSON.stringify({
          success: true,
          msg: 'ok',
          data: { id: 'cat-1', name: 'RAG', description: 'desc', createdAtUtc: '2026-04-27T00:00:00Z', updatedAtUtc: null },
        }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }

      if (method === 'PUT' && url.endsWith('/api/glossary/categories/cat-1')) {
        return new Response(JSON.stringify({
          success: true,
          msg: 'ok',
          data: { id: 'cat-1', name: 'Agent', description: 'updated', createdAtUtc: '2026-04-27T00:00:00Z', updatedAtUtc: '2026-04-28T00:00:00Z' },
        }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }

      if (method === 'DELETE' && url.endsWith('/api/glossary/categories/cat-1')) {
        return new Response(null, { status: 204 });
      }

      if (method === 'POST' && url.endsWith('/api/glossary/terms')) {
        return new Response(JSON.stringify({
          success: true,
          msg: 'ok',
          data: { id: 'term-1', categoryId: 'cat-1', term: 'Embedding', synonyms: ['向量化'], createdAtUtc: '2026-04-27T00:00:00Z', updatedAtUtc: null },
        }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }

      if (method === 'PUT' && url.endsWith('/api/glossary/terms/term-1')) {
        return new Response(JSON.stringify({
          success: true,
          msg: 'ok',
          data: { id: 'term-1', categoryId: 'cat-1', term: 'Retriever', synonyms: ['检索器'], createdAtUtc: '2026-04-27T00:00:00Z', updatedAtUtc: '2026-04-28T00:00:00Z' },
        }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }

      if (method === 'DELETE' && url.endsWith('/api/glossary/terms/term-1')) {
        return new Response(null, { status: 204 });
      }

      if (method === 'POST' && url.endsWith('/api/glossary/terms/import')) {
        return new Response(JSON.stringify({
          success: true,
          msg: 'ok',
          data: { importedCount: 1, errors: [] },
        }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }

      throw new Error(`Unexpected fetch: ${method} ${url}`);
    });

    const client = createQueryClient();
    const invalidateSpy = vi.spyOn(client, 'invalidateQueries');
    render(<GlossaryMutationHarness />, { wrapper: ({ children }) => <QueryWrapper client={client}>{children}</QueryWrapper> });

    fireEvent.click(screen.getByRole('button', { name: 'create-category' }));
    fireEvent.click(screen.getByRole('button', { name: 'update-category' }));
    fireEvent.click(screen.getByRole('button', { name: 'delete-category' }));
    fireEvent.click(screen.getByRole('button', { name: 'create-term' }));
    fireEvent.click(screen.getByRole('button', { name: 'update-term' }));
    fireEvent.click(screen.getByRole('button', { name: 'delete-term' }));
    fireEvent.click(screen.getByRole('button', { name: 'import-terms' }));

    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: glossaryQueryKeys.all() });
    });

    expect(invalidateSpy).toHaveBeenCalledTimes(7);
  });

  it('shows row errors returned by import api and keeps successful count visible', async () => {
    const user = userEvent.setup();
    await switchTestLanguage('en-US');
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;

      if (init?.method === 'POST' && url.endsWith('/api/glossary/terms/import')) {
        return new Response(JSON.stringify({
          success: true,
          msg: 'ok',
          data: {
            importedCount: 2,
            errors: ['第 4 行缺少 term', '第 7 行分类不存在'],
          },
        }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }

      throw new Error(`Unexpected fetch: ${url}`);
    });

    const client = createQueryClient();
    render(<TermImportDrawer open categoryId="1" onClose={vi.fn()} />, {
      wrapper: ({ children }) => <QueryWrapper client={client}>{children}</QueryWrapper>,
    });

    const file = new File(['term,category\nEmbedding,RAG'], 'terms.csv', { type: 'text/csv' });
    const input = document.getElementById('glossary-term-import-file') as HTMLInputElement;
    await user.upload(input, file);

    expect(screen.getByText('terms.csv')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Import terms' }));

    expect(await screen.findByText('Imported 2 terms')).toBeInTheDocument();
    expect(screen.getByText('第 4 行缺少 term')).toBeInTheDocument();
    expect(screen.getByText('第 7 行分类不存在')).toBeInTheDocument();

    const [, init] = fetchMock.mock.calls[0]!;
    expect(init?.body).toBeInstanceOf(FormData);
  });

  it('only advertises supported import file types', () => {
    const client = createQueryClient();
    render(<TermImportDrawer open categoryId="1" onClose={vi.fn()} />, {
      wrapper: ({ children }) => <QueryWrapper client={client}>{children}</QueryWrapper>,
    });

    expect(document.getElementById('glossary-term-import-file')).toHaveAttribute('accept', '.csv');
  });
});
