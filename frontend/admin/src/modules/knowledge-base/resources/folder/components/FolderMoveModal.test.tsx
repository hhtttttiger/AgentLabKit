import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { FolderMoveModal } from './FolderMoveModal';

const moveMutateAsync = vi.fn();

vi.mock('../hooks', () => ({
  useFolderList: () => ({
    data: [
      { id: 'folder-1', knowledgeBaseId: 'kb-1', parentFolderId: null, name: '产品文档', sortOrder: 0, createdAtUtc: '2026-05-08T00:00:00Z' },
      { id: 'folder-2', knowledgeBaseId: 'kb-1', parentFolderId: null, name: '帮助中心', sortOrder: 1, createdAtUtc: '2026-05-08T00:00:00Z' },
    ],
  }),
  useFolderMutations: () => ({
    move: {
      mutateAsync: moveMutateAsync,
    },
  }),
}));

describe('FolderMoveModal', () => {
  afterEach(() => {
    moveMutateAsync.mockReset();
  });

  it('moves a document to the root option', async () => {
    const user = userEvent.setup();
    const onMoveDocument = vi.fn().mockResolvedValue(undefined);
    const onClose = vi.fn();

    render(
      <FolderMoveModal
        kbId="kb-1"
        itemId="doc-1"
        itemType="document"
        open
        onClose={onClose}
        onMoveDocument={onMoveDocument}
      />,
    );

    await user.click(screen.getByRole('button', { name: '根目录' }));
    await user.click(screen.getByRole('button', { name: '移动' }));

    expect(onMoveDocument).toHaveBeenCalledWith(null);
    expect(onClose).toHaveBeenCalled();
  });

  it('moves a folder with the selected target parent', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    moveMutateAsync.mockResolvedValue(undefined);

    render(
      <FolderMoveModal
        kbId="kb-1"
        itemId="folder-1"
        itemType="folder"
        excludeFolderId="folder-1"
        open
        onClose={onClose}
      />,
    );

    expect(screen.queryByRole('button', { name: '产品文档' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '帮助中心' }));
    await user.click(screen.getByRole('button', { name: '移动' }));

    expect(moveMutateAsync).toHaveBeenCalledWith({
      folderId: 'folder-1',
      data: { targetParentFolderId: 'folder-2' },
    });
    expect(onClose).toHaveBeenCalled();
  });
});
