import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { FolderManagerDrawer } from './FolderManagerDrawer';

const { useFolderListMock, useFolderMutationsMock } = vi.hoisted(() => ({
  useFolderListMock: vi.fn(),
  useFolderMutationsMock: vi.fn(),
}));

vi.mock('../hooks', () => ({
  useFolderList: useFolderListMock,
  useFolderMutations: useFolderMutationsMock,
}));

vi.mock('./FolderCreateModal', () => ({
  FolderCreateModal: ({ open, parentFolderId }: { open: boolean; parentFolderId: string | null }) => (
    open ? <div data-testid="folder-create-modal">{parentFolderId ?? 'root'}</div> : null
  ),
}));

vi.mock('./FolderMoveModal', () => ({
  FolderMoveModal: () => <div data-testid="folder-move-modal" />,
}));

describe('FolderManagerDrawer', () => {
  afterEach(() => {
    useFolderListMock.mockReset();
    useFolderMutationsMock.mockReset();
  });

  it('shows an empty state when no folders exist', () => {
    useFolderListMock.mockReturnValue({ data: [] });
    useFolderMutationsMock.mockReturnValue({
      remove: { mutateAsync: vi.fn(), isPending: false },
      update: { mutateAsync: vi.fn(), isPending: false },
    });

    render(<FolderManagerDrawer kbId="kb-1" open onClose={vi.fn()} />);

    expect(screen.getByText('暂无文件夹')).toBeInTheDocument();
  });

  it('renders nested folders and opens create-root modal', async () => {
    const user = userEvent.setup();

    useFolderListMock.mockReturnValue({
      data: [
        { id: 'folder-1', knowledgeBaseId: 'kb-1', parentFolderId: null, name: '产品文档', sortOrder: 0, createdAtUtc: '2026-05-08T00:00:00Z' },
        { id: 'folder-2', knowledgeBaseId: 'kb-1', parentFolderId: 'folder-1', name: 'API 参考', sortOrder: 0, createdAtUtc: '2026-05-08T00:00:00Z' },
      ],
    });
    useFolderMutationsMock.mockReturnValue({
      remove: { mutateAsync: vi.fn(), isPending: false },
      update: { mutateAsync: vi.fn(), isPending: false },
    });

    render(<FolderManagerDrawer kbId="kb-1" open onClose={vi.fn()} />);

    expect(screen.getByText('产品文档')).toBeInTheDocument();
    expect(screen.getByText('API 参考')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '新建根文件夹' }));

    expect(screen.getByTestId('folder-create-modal')).toHaveTextContent('root');
  });
});
