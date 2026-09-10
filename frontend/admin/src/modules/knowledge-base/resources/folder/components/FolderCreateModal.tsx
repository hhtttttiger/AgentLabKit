import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation(['common', 'knowledgeBase']);
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
      setError(t('knowledgeBase:folderCreate.nameRequired'));
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
      title={t('knowledgeBase:documents.createFolder')}
      description={t('knowledgeBase:folderCreate.description')}
      onClose={onClose}
      widthClassName="max-w-lg"
      footer={(
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose}>
            {t('common:actions.cancel')}
          </Button>
          <Button onClick={handleSubmit} disabled={create.isPending}>
            {create.isPending ? t('knowledgeBase:folderCreate.creating') : t('knowledgeBase:folderCreate.submit')}
          </Button>
        </div>
      )}
    >
      <div className="space-y-4">
        <TextField
          label={t('knowledgeBase:folderCreate.nameLabel')}
          value={name}
          autoFocus
          maxLength={200}
          placeholder={t('knowledgeBase:folderCreate.namePlaceholder')}
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
