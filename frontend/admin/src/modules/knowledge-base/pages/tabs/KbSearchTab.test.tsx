import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { KbSearchTab } from './KbSearchTab';
import { ApiError } from '@/shared/api/errors';

const apiMocks = vi.hoisted(() => ({
  searchKnowledgeBase: vi.fn(),
}));

const hookMocks = vi.hoisted(() => ({
  useKbDetail: vi.fn(() => ({
    isLoading: false,
    data: {
      id: 'kb-1',
      name: '知识库',
      description: 'desc',
      sourceType: 'Local',
      documentCount: 1,
      status: 'Active',
      settingsJson: '{"version":1,"provider":"local","local":{"maxLength":1024,"overlap":0,"splitter":"recursive","indexes":["embedding","full_text"]},"recallSources":[]}',
      createdAtUtc: '2026-04-24T00:00:00Z',
    },
  })),
}));

vi.mock('../../resources/search/api', () => ({
  searchKnowledgeBase: apiMocks.searchKnowledgeBase,
}));

vi.mock('../../resources/knowledge-base/hooks', () => ({
  useKbDetail: hookMocks.useKbDetail,
}));

function renderPage() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/knowledge-bases/kb-1/search']}>
        <Routes>
          <Route path="/knowledge-bases/:kbId/search" element={<KbSearchTab />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('KbSearchTab', () => {
  afterEach(() => {
    vi.clearAllMocks();
    hookMocks.useKbDetail.mockReturnValue({
      isLoading: false,
      data: {
        id: 'kb-1',
        name: '知识库',
        description: 'desc',
        sourceType: 'Local',
        documentCount: 1,
        status: 'Active',
        settingsJson: '{"version":1,"provider":"local","local":{"maxLength":1024,"overlap":0,"splitter":"recursive","indexes":["embedding","full_text"]},"recallSources":[]}',
        createdAtUtc: '2026-04-24T00:00:00Z',
      },
    });
  });

  it('keeps rendering score labels for the mode that produced the current results', async () => {
    const user = userEvent.setup();
    apiMocks.searchKnowledgeBase.mockResolvedValue({
      results: [
        {
          segmentId: 1,
          documentId: 101,
          content: 'shipping policy',
          score: 0.93,
          vectorScore: 0.88,
          fulltextScore: 0.51,
        },
      ],
    });

    renderPage();

    await user.type(screen.getByLabelText('搜索内容'), 'shipping');
    await user.click(screen.getByRole('button', { name: '搜索' }));

    await waitFor(() => {
      expect(screen.getByText('向量分')).toBeInTheDocument();
    });
    expect(screen.getByText('提示：混合检索下，向量分和全文分是各自召回通道内的归一化结果，综合分是融合排序分。')).toBeInTheDocument();
    expect(screen.getByText('全文分')).toBeInTheDocument();
    expect(screen.getByText('综合分')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /向量召回/i }));

    expect(screen.getByText('向量分')).toBeInTheDocument();
    expect(screen.getByText('全文分')).toBeInTheDocument();
    expect(screen.getByText('综合分')).toBeInTheDocument();
    expect(screen.queryByText('相似度')).not.toBeInTheDocument();
  });

  it('hides the hybrid score explanation for vector-only searches', async () => {
    const user = userEvent.setup();
    apiMocks.searchKnowledgeBase.mockResolvedValue({
      results: [
        {
          segmentId: 1,
          documentId: 101,
          content: 'shipping policy',
          score: 0.46,
          vectorScore: 0.46,
        },
      ],
    });

    renderPage();

    await user.click(screen.getByRole('button', { name: /向量召回/i }));
    await user.type(screen.getByLabelText('搜索内容'), 'shipping');
    await user.click(screen.getByRole('button', { name: '搜索' }));

    await waitFor(() => {
      expect(screen.getByText('相似度')).toBeInTheDocument();
    });
    expect(screen.queryByText('提示：混合检索下，向量分和全文分是各自召回通道内的归一化结果，综合分是融合排序分。')).not.toBeInTheDocument();
  });

  it('shows backend error message when knowledge search fails', async () => {
    const user = userEvent.setup();
    apiMocks.searchKnowledgeBase.mockRejectedValue(new ApiError('知识库召回服务不可用', 502));

    renderPage();

    await user.type(screen.getByLabelText('搜索内容'), '第一卷');
    await user.click(screen.getByRole('button', { name: '搜索' }));

    await waitFor(() => {
      expect(screen.getByText('知识库召回服务不可用')).toBeInTheDocument();
    });
  });

  it('renders search form for azure provider knowledge bases', async () => {
    hookMocks.useKbDetail.mockReturnValue({
      isLoading: false,
      data: {
        id: 'kb-1',
        name: 'Azure KB',
        description: 'desc',
        sourceType: 'Local',
        documentCount: 1,
        status: 'Active',
        settingsJson: '{"version":1,"provider":"azure","azure":{"profileId":"azure-search-default"}}',
        createdAtUtc: '2026-04-24T00:00:00Z',
      },
    });

    renderPage();

    expect(screen.getByLabelText('搜索内容')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '搜索' })).toBeInTheDocument();
  });

  it('only shows hybrid and fulltext modes for azure provider', async () => {
    hookMocks.useKbDetail.mockReturnValue({
      isLoading: false,
      data: {
        id: 'kb-1',
        name: 'Azure KB',
        description: 'desc',
        sourceType: 'Local',
        documentCount: 1,
        status: 'Active',
        settingsJson: '{"version":1,"provider":"azure","azure":{"profileId":"azure-search-default"}}',
        createdAtUtc: '2026-04-24T00:00:00Z',
      },
    });

    renderPage();

    expect(screen.getByRole('button', { name: /混合召回/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /全文召回/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /向量召回/i })).not.toBeInTheDocument();
  });
});
