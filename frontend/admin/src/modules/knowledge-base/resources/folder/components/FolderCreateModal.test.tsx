import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { FolderCreateModal } from './FolderCreateModal';

const createMutateAsync = vi.fn();

vi.mock('../hooks', () => ({
  useFolderMutations: () => ({
    create: {
      mutateAsync: createMutateAsync,
      isPending: false,
    },
  }),
}));

describe('FolderCreateModal', () => {
  afterEach(() => {
    createMutateAsync.mockReset();
  });

  it('shows an inline error when the folder name is blank', async () => {
    const user = userEvent.setup();

    render(
      <FolderCreateModal
        kbId="kb-1"
        parentFolderId={null}
        open
        onClose={vi.fn()}
      />,
    );

    await user.click(screen.getByRole('button', { name: '创建文件夹' }));

    expect(screen.getByText('文件夹名称不能为空')).toBeInTheDocument();
    expect(createMutateAsync).not.toHaveBeenCalled();
  });

  it('submits a trimmed folder name and closes on success', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    createMutateAsync.mockResolvedValue(undefined);

    render(
      <FolderCreateModal
        kbId="kb-1"
        parentFolderId="parent-1"
        open
        onClose={onClose}
      />,
    );

    await user.type(screen.getByLabelText('文件夹名称'), '  产品文档  ');
    await user.click(screen.getByRole('button', { name: '创建文件夹' }));

    expect(createMutateAsync).toHaveBeenCalledWith({ name: '产品文档', parentFolderId: 'parent-1' });
    expect(onClose).toHaveBeenCalled();
  });
});
