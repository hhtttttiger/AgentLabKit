import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Button } from './Button';
import { FormModal } from './FormModal';
import { TextField } from './FormFields';
import { InlineMessage } from './InlineMessage';
import { useToast } from './Toast';
import { getErrorMessage } from '@/shared/api/errors';
import { changePassword } from '@/shared/auth/api';

export function ChangePasswordDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const { toast } = useToast();
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => changePassword({ oldPassword, newPassword }),
    onSuccess: () => {
      toast(t('toast.operationSuccess'));
      handleClose();
    },
    onError: (err) => {
      setError(getErrorMessage(err));
    },
  });

  function handleClose() {
    setOldPassword('');
    setNewPassword('');
    setConfirmPassword('');
    setError(null);
    onClose();
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (newPassword.length < 8) {
      setError(t('shared.auth.changePassword.tooShort'));
      return;
    }
    if (newPassword !== confirmPassword) {
      setError(t('shared.auth.changePassword.mismatch'));
      return;
    }

    mutation.mutate();
  }

  return (
    <FormModal
      open={open}
      title={t('shared.auth.changePassword.title')}
      onClose={handleClose}
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {error && <InlineMessage tone="error">{error}</InlineMessage>}

        <TextField
          label={t('shared.auth.changePassword.currentPassword')}
          type="password"
          value={oldPassword}
          onChange={(e) => setOldPassword(e.target.value)}
          required
          autoFocus
        />
        <TextField
          label={t('shared.auth.changePassword.newPassword')}
          type="password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          required
        />
        <TextField
          label={t('shared.auth.changePassword.confirmPassword')}
          type="password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          required
        />

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" type="button" onClick={handleClose}>
            {t('actions.cancel')}
          </Button>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? t('shared.auth.changePassword.saving') : t('shared.auth.changePassword.save')}
          </Button>
        </div>
      </form>
    </FormModal>
  );
}
