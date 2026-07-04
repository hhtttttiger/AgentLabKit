import { Button } from './Button';
import { InlineMessage } from './InlineMessage';
import { Modal } from './Modal';
import { useTranslation } from 'react-i18next';

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  loading,
  error,
  onConfirm,
  onClose,
  tone = 'danger',
  body,
}: {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  loading?: boolean;
  error?: string | null;
  onConfirm: () => void;
  onClose: () => void;
  tone?: 'danger' | 'primary';
  body?: string;
}) {
  const { t } = useTranslation('common');
  const isDanger = tone === 'danger';

  return (
    <Modal
      open={open}
      title={title}
      description={description}
      onClose={onClose}
      widthClassName="max-w-xl"
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose}>
            {t('actions.cancel')}
          </Button>
          <Button variant={isDanger ? 'danger' : 'primary'} onClick={onConfirm} disabled={loading}>
            {loading ? t('states.processing') : confirmLabel}
          </Button>
        </div>
      }
    >
      <div className="space-y-3">
        {error && <InlineMessage tone="error">{error}</InlineMessage>}
        <div className={
          isDanger
            ? 'rounded-[2px] border border-error/20 bg-error-subtle p-4 text-sm leading-6 text-error-text'
            : 'rounded-[2px] border border-primary/20 bg-primary-subtle p-4 text-sm leading-6 text-text-secondary'
        }>
          {body ?? (isDanger ? t('dialogs.confirm.dangerBody') : t('dialogs.confirm.defaultBody'))}
        </div>
      </div>
    </Modal>
  );
}
