import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { KbOverviewTab } from './KbOverviewTab';
import { KnowledgeBaseLayout } from '../KnowledgeBaseLayout';

vi.mock('../../resources/knowledge-base/hooks', () => ({
  useKbDetail: () => ({
    isLoading: false,
    data: {
      id: 'kb-1',
      name: '客服知识库',
      description: 'desc',
      sourceType: 'Local',
      documentCount: 3,
      status: 'Active',
      settingsJson: '{"version":1,"provider":"azure","azure":{"profileId":"azure-search-default"}}',
      createdAtUtc: '2026-04-20T00:00:00Z',
    },
  }),
  useKbMutations: () => ({
    update: {
      isPending: false,
      mutate: vi.fn(),
    },
  }),
}));

vi.mock('../../resources/ranking/hooks', () => ({
  useTopRecalledDocuments: () => ({
    isLoading: false,
    data: [
      {
        documentId: 'doc-file',
        knowledgeBaseId: 'kb-1',
        sourceType: 'File',
        fileName: 'refund-policy.pdf',
        ingestStatus: 'Completed',
        recallCount: 12,
        lastRecalledAtUtc: '2026-04-20T08:00:00Z',
        createdAtUtc: '2026-04-19T00:00:00Z',
      },
      {
        documentId: 'doc-qa',
        knowledgeBaseId: 'kb-1',
        sourceType: 'QaPair',
        qaQuestion: '退款多久到账？',
        ingestStatus: 'Completed',
        recallCount: 8,
        lastRecalledAtUtc: '2026-04-20T09:00:00Z',
        createdAtUtc: '2026-04-19T00:00:00Z',
      },
    ],
  }),
}));

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/knowledge-base/kb-1']}>
      <Routes>
        <Route path="/knowledge-base/:kbId" element={<KnowledgeBaseLayout />}>
          <Route index element={<KbOverviewTab />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('KbOverviewTab', () => {
  it('renders mixed top recalled items with type labels', () => {
    renderPage();

    expect(screen.getByText('召回文档 / QA Top 30')).toBeInTheDocument();
    expect(screen.getByText('Azure')).toBeInTheDocument();
    expect(screen.getByText('azure-search-default')).toBeInTheDocument();
    expect(screen.getByText('refund-policy.pdf')).toBeInTheDocument();
    expect(screen.getByText('退款多久到账？')).toBeInTheDocument();
    expect(screen.getAllByText('文件')[0]).toBeInTheDocument();
    expect(screen.getAllByText('QA')[0]).toBeInTheDocument();
  });

  it('renders azure provider summary from settingsJson', () => {
    renderPage();

    expect(screen.getByText('Azure')).toBeInTheDocument();
    expect(screen.getByText('azure-search-default')).toBeInTheDocument();
  });

  it('renders edit action in header and opens edit drawer', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole('button', { name: '编辑' }));

    expect(screen.getByText('编辑知识库')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '保存' })).toBeInTheDocument();
  });
});
