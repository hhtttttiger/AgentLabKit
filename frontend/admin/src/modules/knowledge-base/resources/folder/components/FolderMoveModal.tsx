import { useEffect, useMemo, useState } from 'react';
import { ChevronRight, Folder } from 'lucide-react';
import { Button } from '@/shared/ui/Button';
import { Modal } from '@/shared/ui/Modal';
import { cn } from '@/shared/lib/cn';
import type { KbFolderView } from '../../../lib/contracts';
import { useFolderList, useFolderMutations } from '../hooks';

type Props = {
  kbId: string;
  itemId: string;
  itemType: 'folder' | 'document';
  excludeFolderId?: string;
  open: boolean;
  onClose: () => void;
  onMoveDocument?: (targetFolderId: string | null) => Promise<void>;
};

const ROOT_ID = '__root__';

export function FolderMoveModal({
  kbId,
  itemId,
  itemType,
  excludeFolderId,
  open,
  onClose,
  onMoveDocument,
}: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isMoving, setIsMoving] = useState(false);
  const { data: folders = [] } = useFolderList(kbId);
  const { move } = useFolderMutations(kbId);

  useEffect(() => {
    if (open) {
      setSelectedId(null);
      setIsMoving(false);
    }
  }, [open]);

  const options = useMemo(() => {
    const visibleFolders = itemType === 'folder'
      ? folders.filter((folder) => folder.id !== excludeFolderId && folder.parentFolderId !== excludeFolderId)
      : folders;

    const rootOption: KbFolderView = {
      id: ROOT_ID,
      knowledgeBaseId: kbId,
      parentFolderId: null,
      name: '根目录',
      sortOrder: -1,
      createdAtUtc: '',
    };

    return [rootOption, ...visibleFolders];
  }, [excludeFolderId, folders, itemType, kbId]);

  const handleMove = async () => {
    if (!selectedId) {
      return;
    }

    const targetFolderId = selectedId === ROOT_ID ? null : selectedId;

    setIsMoving(true);
    try {
      if (itemType === 'folder') {
        await move.mutateAsync({
          folderId: itemId,
          data: { targetParentFolderId: targetFolderId },
        });
      } else {
        await onMoveDocument?.(targetFolderId);
      }

      onClose();
    } finally {
      setIsMoving(false);
    }
  };

  return (
    <Modal
      open={open}
      title="移动到文件夹"
      description="选择新的目标位置。根目录表示不放入任何文件夹。"
      onClose={onClose}
      widthClassName="max-w-lg"
      footer={(
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose}>
            取消
          </Button>
          <Button onClick={handleMove} disabled={!selectedId || isMoving}>
            {isMoving ? '移动中...' : '移动'}
          </Button>
        </div>
      )}
    >
      <div className="space-y-2">
        {options.map((folder) => {
          const active = selectedId === folder.id;
          return (
            <button
              key={folder.id}
              type="button"
              className={cn(
                'flex min-h-control w-full items-center gap-3 rounded-[2px] border px-4 py-3 text-left text-sm transition',
                active
                  ? 'border-primary bg-primary-subtle text-text'
                  : 'border-border bg-surface hover:border-primary/30 hover:bg-primary-subtle/30',
              )}
              onClick={() => setSelectedId(folder.id)}
            >
              <Folder size={16} className="shrink-0 text-text-secondary" />
              <span className="flex-1 font-medium">{folder.name}</span>
              {active ? <ChevronRight size={16} className="shrink-0 text-primary" /> : null}
            </button>
          );
        })}
      </div>
    </Modal>
  );
}
