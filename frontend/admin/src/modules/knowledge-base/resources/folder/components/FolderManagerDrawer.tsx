import type { ReactNode } from 'react';
import { useMemo, useState } from 'react';
import { Folder, FolderOpen, Move, Pencil, Plus, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/shared/ui/Button';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { FormModal } from '@/shared/ui/FormModal';
import { EmptyState } from '@/shared/ui/EmptyState';
import { cn } from '@/shared/lib/cn';
import type { KbFolderView } from '../../../lib/contracts';
import { useFolderList, useFolderMutations } from '../hooks';
import { FolderCreateModal } from './FolderCreateModal';
import { FolderMoveModal } from './FolderMoveModal';

type Props = {
  kbId: string;
  open: boolean;
  onClose: () => void;
};

export function FolderManagerDrawer({ kbId, open, onClose }: Props) {
  const { t } = useTranslation(['common', 'knowledgeBase']);
  const { data: folders = [] } = useFolderList(kbId);
  const { remove, update } = useFolderMutations(kbId);
  const [createParentId, setCreateParentId] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [deletingFolder, setDeletingFolder] = useState<KbFolderView | null>(null);
  const [movingFolder, setMovingFolder] = useState<KbFolderView | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');

  const rootFolders = useMemo(
    () => folders
      .filter((folder) => folder.parentFolderId === null)
      .sort((left, right) => left.sortOrder - right.sortOrder || left.name.localeCompare(right.name)),
    [folders],
  );

  const startRenaming = (folder: KbFolderView) => {
    setRenamingId(folder.id);
    setRenameValue(folder.name);
  };

  const finishRenaming = async (folder: KbFolderView) => {
    const nextName = renameValue.trim();
    if (nextName && nextName !== folder.name) {
      await update.mutateAsync({ folderId: folder.id, data: { name: nextName } });
    }
    setRenamingId(null);
    setRenameValue('');
  };

  const renderFolder = (folder: KbFolderView, depth = 0): ReactNode => {
    const children = folders
      .filter((item) => item.parentFolderId === folder.id)
      .sort((left, right) => left.sortOrder - right.sortOrder || left.name.localeCompare(right.name));

    const isRenaming = renamingId === folder.id;

    return (
      <div key={folder.id} className="space-y-1">
        <div
          className="group flex items-center gap-2 rounded-[2px] border border-transparent px-3 py-2 hover:border-border hover:bg-background-subtle"
          style={{ paddingLeft: `${12 + depth * 18}px` }}
        >
          {children.length > 0 ? (
            <FolderOpen size={16} className="shrink-0 text-text-secondary" />
          ) : (
            <Folder size={16} className="shrink-0 text-text-secondary" />
          )}

          {isRenaming ? (
            <input
              value={renameValue}
              autoFocus
              onChange={(event) => setRenameValue(event.target.value)}
              onBlur={() => { void finishRenaming(folder); }}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault();
                  void finishRenaming(folder);
                }
                if (event.key === 'Escape') {
                  setRenamingId(null);
                  setRenameValue('');
                }
              }}
              className="min-h-control flex-1 rounded-[2px] border border-border-strong bg-surface px-3 text-sm text-text outline-none focus:border-transparent focus:ring-2 focus:ring-state-focus/40"
            />
          ) : (
            <span className="flex-1 truncate text-sm font-medium text-text">{folder.name}</span>
          )}

          {!isRenaming ? (
            <div className="flex items-center gap-1 opacity-100 transition sm:opacity-0 sm:group-hover:opacity-100">
              <Button
                variant="ghost"
                className="h-8 px-2 text-xs"
                onClick={() => {
                  setCreateParentId(folder.id);
                  setCreateOpen(true);
                }}
                aria-label={`在 ${folder.name} 下新建子文件夹`}
                title="新建子文件夹"
              >
                <Plus size={14} />
              </Button>
              <Button
                variant="ghost"
                className="h-8 px-2 text-xs"
                onClick={() => startRenaming(folder)}
                aria-label={`重命名 ${folder.name}`}
              >
                <Pencil size={14} />
              </Button>
              <Button
                variant="ghost"
                className="h-8 px-2 text-xs"
                onClick={() => setMovingFolder(folder)}
                aria-label={`移动 ${folder.name}`}
              >
                <Move size={14} />
              </Button>
              <Button
                variant="ghost"
                className={cn('h-8 px-2 text-xs text-error-text hover:bg-error-subtle hover:text-error-text')}
                onClick={() => setDeletingFolder(folder)}
                aria-label={`删除 ${folder.name}`}
              >
                <Trash2 size={14} />
              </Button>
            </div>
          ) : null}
        </div>

        {children.map((child) => renderFolder(child, depth + 1))}
      </div>
    );
  };

  return (
    <>
      <FormModal
        open={open}
        title="管理文件夹"
        description="按层级整理知识库内容。支持新建、重命名、移动和删除。"
        onClose={onClose}
        widthClassName="max-w-xl"
        footer={(
          <div className="flex justify-end">
            <Button
              onClick={() => {
                setCreateParentId(null);
                setCreateOpen(true);
              }}
            >
              <Plus size={16} />
              新建根文件夹
            </Button>
          </div>
        )}
      >
        <div className="space-y-2">
          {rootFolders.length === 0 ? (
            <EmptyState title={t('knowledgeBase:detail.folderEmptyTitle')} />
          ) : (
            rootFolders.map((folder) => renderFolder(folder))
          )}
        </div>
      </FormModal>

      <FolderCreateModal
        kbId={kbId}
        parentFolderId={createParentId}
        open={createOpen}
        onClose={() => setCreateOpen(false)}
      />

      {movingFolder ? (
        <FolderMoveModal
          kbId={kbId}
          itemId={movingFolder.id}
          itemType="folder"
          excludeFolderId={movingFolder.id}
          open={!!movingFolder}
          onClose={() => setMovingFolder(null)}
        />
      ) : null}

      <ConfirmDialog
        open={!!deletingFolder}
        title="删除文件夹"
        description={deletingFolder
          ? `确认删除「${deletingFolder.name}」？该文件夹下的子文件夹和文档也会被一并删除。`
          : '确认删除当前文件夹？'}
        confirmLabel="删除"
        loading={remove.isPending}
        onConfirm={() => {
          if (!deletingFolder) {
            return;
          }
          remove.mutateAsync(deletingFolder.id).finally(() => setDeletingFolder(null));
        }}
        onClose={() => setDeletingFolder(null)}
      />
    </>
  );
}
