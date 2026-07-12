import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Button } from './Button';
import { FormModal } from './FormModal';
import { TextField } from './FormFields';
import { InlineMessage } from './InlineMessage';
import { useToast } from './Toast';
import { getErrorMessage } from '@/shared/api/errors';
import { getMe, updateProfile } from '@/shared/auth/api';

export function ProfileDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const meQuery = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: getMe,
    enabled: open,
  });

  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (meQuery.data) {
      setDisplayName(meQuery.data.displayName ?? '');
      setEmail(meQuery.data.email ?? '');
    }
  }, [meQuery.data]);

  const mutation = useMutation({
    mutationFn: () => updateProfile({
      displayName: displayName || undefined,
      email: email || undefined,
    }),
    onSuccess: () => {
      toast(t('toast.updated'));
      queryClient.invalidateQueries({ queryKey: ['auth', 'me'] });
      handleClose();
    },
    onError: (err) => {
      setError(getErrorMessage(err));
    },
  });

  function handleClose() {
    setError(null);
    onClose();
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    mutation.mutate();
  }

  return (
    <FormModal
      open={open}
      title={t('shared.auth.profile.title')}
      onClose={handleClose}
    >
      {meQuery.isLoading ? (
        <div className="py-8 text-center text-text-muted">{t('states.loading')}</div>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {error && <InlineMessage tone="error">{error}</InlineMessage>}

          <TextField
            label={t('shared.auth.profile.username')}
            value={meQuery.data?.username ?? ''}
            disabled
          />
          <TextField
            label={t('shared.auth.profile.displayName')}
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
          />
          <TextField
            label={t('shared.auth.profile.email')}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" type="button" onClick={handleClose}>
              {t('actions.cancel')}
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? t('shared.auth.profile.saving') : t('shared.auth.profile.save')}
            </Button>
          </div>
        </form>
      )}
    </FormModal>
  );
}
