import { useEffect, useState } from 'react';
import { Button } from '@/shared/ui/Button';
import { TextField } from '@/shared/ui/FormFields';
import { Modal } from '@/shared/ui/Modal';
import { useFolderMutations } from '../hooks';

type Props = {
  kbId: string;
  parentFolderId: string | null;
  open: boolean;
  onClose: () => void;
};

export function FolderCreateModal({ kbId, parentFolderId, open, onClose }: Props) {
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const { create } = useFolderMutations(kbId);

  useEffect(() => {
    if (!open) {
      setName('');
      setError(null);
    }
  }, [open]);

  const handleSubmit = async () => {
    const trimmedName = name.trim();
    if (!trimmedName) {
      setError('文件夹名称不能为空');
      return;
    }

    await create.mutateAsync({
      name: trimmedName,
      parentFolderId,
    });

    setName('');
    setError(null);
    onClose();
  };

  return (
    <Modal
      open={open}
      title="新建文件夹"
      description="文件夹用于整理知识库中的文档，支持多层级管理。"
      onClose={onClose}
      widthClassName="max-w-lg"
      footer={(
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose}>
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={create.isPending}>
            {create.isPending ? '创建中...' : '创建文件夹'}
          </Button>
        </div>
      )}
    >
      <div className="space-y-4">
        <TextField
          label="文件夹名称"
          value={name}
          autoFocus
          maxLength={200}
          placeholder="例如：产品文档"
          error={error}
          onChange={(event) => {
            setName(event.target.value);
            if (error) {
              setError(null);
            }
          }}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault();
              void handleSubmit();
            }
          }}
        />
      </div>
    </Modal>
  );
}
