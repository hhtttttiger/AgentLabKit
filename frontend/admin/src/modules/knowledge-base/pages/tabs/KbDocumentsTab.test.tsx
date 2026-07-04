import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { KbDocumentsTab } from './KbDocumentsTab';
import type { KbDocumentView, KbFolderView } from '../../lib/contracts';

let currentDocuments: KbDocumentView[] = [];
let currentFolders: KbFolderView[] = [];
let lastDocumentFilters: Record<string, unknown> | null = null;
const toastMock = vi.fn();
const mutationMocks = {
  upload: { mutate: vi.fn(), isPending: false },
  importQa: { mutate: vi.fn(), isPending: false },
  createQa: { mutate: vi.fn(), isPending: false },
  updateQa: { mutate: vi.fn(), isPending: false },
  remove: { mutate: vi.fn(), mutateAsync: vi.fn(), isPending: false },
  reindex: { mutate: vi.fn(), mutateAsync: vi.fn(), isPending: false },
  moveDoc: { mutateAsync: vi.fn(), isPending: false },
};
const folderMutationMocks = {
  remove: { mutate: vi.fn(), mutateAsync: vi.fn(), isPending: false },
  create: { mutateAsync: vi.fn(), isPending: false },
  update: { mutateAsync: vi.fn(), isPending: false },
  move: { mutateAsync: vi.fn(), isPending: false },
};

vi.mock('../../resources/document/hooks', () => ({
  useDocumentList: (_kbId: string, filters: { folderId?: string }) => {
    lastDocumentFilters = filters;
    const items = currentDocuments.filter((doc) => {
      if (filters.folderId === '0') {
        return (doc.folderId ?? null) === null;
      }
      if (typeof filters.folderId === 'string') {
        return doc.folderId === filters.folderId;
      }
      return true;
    });

    return {
      data: { items, totalCount: items.length, page: 1, pageSize: 20 },
      isLoading: false,
      isFetching: false,
      refetch: vi.fn(),
    };
  },
  useDocumentDetail: (_kbId: string, docId: string) => ({
    data: currentDocuments.find((doc) => doc.id === docId) ?? null,
    isLoading: false,
  }),
  useProcessingStatus: () => ({
    data: { currentStage: 'Completed' },
    isLoading: false,
  }),
  useDocumentIndexes: () => ({
    data: [],
    isLoading: false,
  }),
  useDocumentMutations: () => mutationMocks,
}));

vi.mock('../../resources/folder/hooks', () => ({
  useFolderList: () => ({ data: currentFolders }),
  useFolderMutations: () => folderMutationMocks,
}));

vi.mock('@/shared/ui/Toast', () => ({
  useToast: () => ({ toast: toastMock }),
}));

function createDocument(id: string, ingestStatus: KbDocumentView['ingestStatus']): KbDocumentView {
  return {
    id,
    knowledgeBaseId: 'kb-1',
    sourceType: 'File',
    fileName: `doc-${id}.md`,
    fileSize: 2048,
    ingestStatus,
    createdAtUtc: '2026-04-16T00:00:00Z',
  };
}

function renderPage() {
  return render(
      <MemoryRouter initialEntries={['/knowledge-bases/kb-1/documents']}>
        <Routes>
          <Route path="/knowledge-bases/:kbId/documents" element={<KbDocumentsTab />} />
        </Routes>
      </MemoryRouter>
  );
}

describe('KbDocumentsTab', () => {
  beforeEach(() => {
    currentDocuments = [];
    currentFolders = [];
    lastDocumentFilters = null;
    toastMock.mockReset();
    mutationMocks.upload.mutate.mockReset();
    mutationMocks.importQa.mutate.mockReset();
    mutationMocks.createQa.mutate.mockReset();
    mutationMocks.updateQa.mutate.mockReset();
    mutationMocks.remove.mutate.mockReset();
    mutationMocks.remove.mutateAsync.mockReset();
    mutationMocks.reindex.mutate.mockReset();
    mutationMocks.reindex.mutateAsync.mockReset();
    mutationMocks.moveDoc.mutateAsync.mockReset();
    folderMutationMocks.remove.mutate.mockReset();
    folderMutationMocks.remove.mutateAsync.mockReset();
    folderMutationMocks.create.mutateAsync.mockReset();
    folderMutationMocks.update.mutateAsync.mockReset();
    folderMutationMocks.move.mutateAsync.mockReset();
    mutationMocks.createQa.mutate.mockImplementation((_data, options) => options?.onSuccess?.());
    mutationMocks.importQa.mutate.mockImplementation((_data, options) => options?.onSuccess?.({
      createdCount: 1,
      updatedCount: 0,
      skippedCount: 0,
      errors: [],
    }));
  });

  it('keeps the detail drawer synced with the latest list item state', () => {
    currentDocuments = [createDocument('doc-1', 'Completed')];
    const view = renderPage();

    fireEvent.click(screen.getByRole('button', { name: /doc-1\.md/i }));
    expect(screen.getByRole('heading', { name: 'doc-doc-1.md' })).toBeInTheDocument();
    expect(screen.getAllByText('已完成')).toHaveLength(2);

    currentDocuments = [createDocument('doc-1', 'Pending')];
    view.rerender(
        <MemoryRouter initialEntries={['/knowledge-bases/kb-1/documents']}>
          <Routes>
            <Route path="/knowledge-bases/:kbId/documents" element={<KbDocumentsTab />} />
          </Routes>
        </MemoryRouter>
    );

    expect(screen.getAllByText('等待中')).toHaveLength(2);
  });

  it('summarizes partial batch reindex failures and keeps failed items selected', async () => {
    currentDocuments = [createDocument('doc-1', 'Completed'), createDocument('doc-2', 'Completed')];
    mutationMocks.reindex.mutateAsync.mockImplementation((id: string) =>
      id === 'doc-1' ? Promise.resolve(undefined) : Promise.reject(new Error('failed')),
    );

    renderPage();

    const checkboxes = screen.getAllByRole('checkbox');
    fireEvent.click(checkboxes[1]!);
    fireEvent.click(checkboxes[2]!);
    fireEvent.click(screen.getByRole('button', { name: '批量重索引' }));

    await waitFor(() => {
      expect(toastMock).toHaveBeenCalledWith('已提交 1 个，仍有 1 个重新索引失败', 'info');
    });

    expect(screen.getByText(/已选择/)).toHaveTextContent('1');
  });

  it('summarizes partial batch delete failures after confirmation', async () => {
    currentDocuments = [createDocument('doc-1', 'Completed'), createDocument('doc-2', 'Completed')];
    mutationMocks.remove.mutateAsync.mockImplementation((id: string) =>
      id === 'doc-1' ? Promise.resolve(undefined) : Promise.reject(new Error('failed')),
    );

    renderPage();

    const checkboxes = screen.getAllByRole('checkbox');
    fireEvent.click(checkboxes[1]!);
    fireEvent.click(checkboxes[2]!);
    fireEvent.click(screen.getByRole('button', { name: '批量删除' }));

    const dialog = screen.getByRole('dialog');
    fireEvent.click(within(dialog).getByRole('button', { name: '删除' }));

    await waitFor(() => {
      expect(toastMock).toHaveBeenCalledWith('已删除 1 个，仍有 1 个删除失败', 'info');
    });

    expect(screen.getByText(/已选择/)).toHaveTextContent('1');
  });

  it('shows recall metrics inside the document detail drawer', () => {
    currentDocuments = [
      {
        id: 'doc-1',
        knowledgeBaseId: 'kb-1',
        sourceType: 'File',
        fileName: 'doc-1.md',
        fileSize: 2048,
        ingestStatus: 'Completed',
        recallCount: 15,
        lastRecalledAtUtc: '2026-04-20T10:00:00Z',
        createdAtUtc: '2026-04-16T00:00:00Z',
      } as KbDocumentView,
    ];

    renderPage();

    fireEvent.click(screen.getByRole('button', { name: /doc-1\.md/i }));

    expect(screen.getByText('累计被召回次数')).toBeInTheDocument();
    expect(screen.getByText('15 次')).toBeInTheDocument();
    expect(screen.getByText('最近召回时间')).toBeInTheDocument();
  });

  it('navigates folders and requests folder-scoped documents', () => {
    currentFolders = [
      {
        id: 'folder-1',
        knowledgeBaseId: 'kb-1',
        parentFolderId: null,
        name: '产品文档',
        sortOrder: 0,
        createdAtUtc: '2026-05-08T00:00:00Z',
      },
    ];
    currentDocuments = [
      createDocument('root-doc', 'Completed'),
      { ...createDocument('nested-doc', 'Completed'), folderId: 'folder-1' },
    ];

    renderPage();

    expect(lastDocumentFilters?.folderId).toBe('0');
    expect(screen.getByText('产品文档')).toBeInTheDocument();
    expect(screen.getByText('doc-root-doc.md')).toBeInTheDocument();
    expect(screen.queryByText('doc-nested-doc.md')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '产品文档' }));

    expect(lastDocumentFilters?.folderId).toBe('folder-1');
    expect(screen.getByText('doc-nested-doc.md')).toBeInTheDocument();
    expect(screen.queryByText('doc-root-doc.md')).not.toBeInTheDocument();
    expect(screen.getByText('全部')).toBeInTheDocument();
  });

  it('uploads into the current folder', async () => {
    currentFolders = [
      {
        id: 'folder-1',
        knowledgeBaseId: 'kb-1',
        parentFolderId: null,
        name: '产品文档',
        sortOrder: 0,
        createdAtUtc: '2026-05-08T00:00:00Z',
      },
    ];

    const view = renderPage();
    fireEvent.click(screen.getByRole('button', { name: '产品文档' }));

    await waitFor(() => {
      expect(lastDocumentFilters?.folderId).toBe('folder-1');
    });

    const fileInput = view.container.querySelector('input[type="file"][multiple]') as HTMLInputElement;
    const file = new File(['hello'], 'guide.md', { type: 'text/markdown' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(mutationMocks.upload.mutate).toHaveBeenCalledWith(
      { file, folderId: 'folder-1' },
      expect.any(Object),
    );
  });

  it('creates qa pairs in the current folder', () => {
    currentFolders = [
      {
        id: 'folder-1',
        knowledgeBaseId: 'kb-1',
        parentFolderId: null,
        name: '产品文档',
        sortOrder: 0,
        createdAtUtc: '2026-05-08T00:00:00Z',
      },
    ];

    renderPage();
    fireEvent.click(screen.getByRole('button', { name: '产品文档' }));
    fireEvent.click(screen.getByRole('button', { name: '创建 QA 对' }));
    fireEvent.change(screen.getByLabelText('问题'), { target: { value: 'Q' } });
    fireEvent.change(screen.getByLabelText('回答'), { target: { value: 'A' } });
    fireEvent.click(screen.getByRole('button', { name: '创建' }));

    expect(mutationMocks.createQa.mutate).toHaveBeenCalledWith(
      { question: 'Q', answer: 'A', folderId: 'folder-1' },
      expect.any(Object),
    );
  });

  it('imports qa pairs into the current folder', () => {
    currentFolders = [
      {
        id: 'folder-1',
        knowledgeBaseId: 'kb-1',
        parentFolderId: null,
        name: '产品文档',
        sortOrder: 0,
        createdAtUtc: '2026-05-08T00:00:00Z',
      },
    ];

    renderPage();
    fireEvent.click(screen.getByRole('button', { name: '产品文档' }));
    fireEvent.click(screen.getByRole('button', { name: '导入 QA' }));

    const file = new File(['Q,A'], 'qa.csv', { type: 'text/csv' });
    const qaImportInput = document.getElementById('qa-import-file') as HTMLInputElement;
    fireEvent.change(qaImportInput, { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: '确认导入' }));

    expect(mutationMocks.importQa.mutate).toHaveBeenCalledWith(
      { file, folderId: 'folder-1' },
      expect.any(Object),
    );
  });

  it('rebuilds breadcrumb when the current folder moves under a new parent', () => {
    currentFolders = [
      {
        id: 'folder-1',
        knowledgeBaseId: 'kb-1',
        parentFolderId: null,
        name: '产品文档',
        sortOrder: 0,
        createdAtUtc: '2026-05-08T00:00:00Z',
      },
    ];

    const view = renderPage();
    fireEvent.click(screen.getByRole('button', { name: '产品文档' }));

    currentFolders = [
      {
        id: 'folder-2',
        knowledgeBaseId: 'kb-1',
        parentFolderId: null,
        name: '归档',
        sortOrder: 0,
        createdAtUtc: '2026-05-08T00:00:00Z',
      },
      {
        id: 'folder-1',
        knowledgeBaseId: 'kb-1',
        parentFolderId: 'folder-2',
        name: '产品文档',
        sortOrder: 0,
        createdAtUtc: '2026-05-08T00:00:00Z',
      },
    ];

    view.rerender(
      <MemoryRouter initialEntries={['/knowledge-bases/kb-1/documents']}>
        <Routes>
          <Route path="/knowledge-bases/:kbId/documents" element={<KbDocumentsTab />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByRole('button', { name: '归档' })).toBeInTheDocument();
    expect(screen.getByText('产品文档')).toBeInTheDocument();
  });
});
