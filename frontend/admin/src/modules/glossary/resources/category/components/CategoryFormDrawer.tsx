import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getErrorMessage } from '@/shared/api/errors';
import { Button } from '@/shared/ui/Button';
import { FormModal } from '@/shared/ui/FormModal';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { TextAreaField, TextField } from '@/shared/ui/FormFields';
import type { GlossaryCategoryCreateRequest, GlossaryCategoryUpdateRequest, GlossaryCategoryView } from '../../../lib/contracts';

type CategoryDraft = {
  name: string;
  description: string;
};

const emptyDraft: CategoryDraft = {
  name: '',
  description: '',
};

function toDraft(value: GlossaryCategoryView | null | undefined): CategoryDraft {
  if (!value) {
    return emptyDraft;
  }

  return {
    name: value.name,
    description: value.description ?? '',
  };
}

export function CategoryFormDrawer({
  open,
  mode,
  initialValue,
  loading,
  error,
  onClose,
  onSubmit,
}: {
  open: boolean;
  mode: 'create' | 'edit';
  initialValue: GlossaryCategoryView | null;
  loading: boolean;
  error: unknown;
  onClose: () => void;
  onSubmit: (payload: GlossaryCategoryCreateRequest | GlossaryCategoryUpdateRequest) => void;
}) {
  const { t } = useTranslation(['common', 'glossary']);
  const [draft, setDraft] = useState<CategoryDraft>(emptyDraft);

  useEffect(() => {
    setDraft(toDraft(initialValue));
  }, [initialValue, open]);

  const nameError = draft.name.trim() ? null : t('glossary:categoryForm.validation.nameRequired');

  return (
    <FormModal
      open={open}
      title={mode === 'create' ? t('glossary:categoryForm.titleCreate') : t('glossary:categoryForm.titleEdit')}
      description={t('glossary:categoryForm.description')}
      onClose={onClose}
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose}>
            {t('glossary:categoryForm.actions.cancel')}
          </Button>
          <Button
            onClick={() =>
              onSubmit({
                name: draft.name.trim(),
                description: draft.description.trim() || undefined,
              })
            }
            disabled={loading || Boolean(nameError)}
          >
            {loading
              ? t('glossary:categoryForm.actions.submitting')
              : mode === 'create'
                ? t('glossary:categoryForm.actions.create')
                : t('glossary:categoryForm.actions.save')}
          </Button>
        </div>
      }
    >
      <div className="space-y-5">
        {error ? <InlineMessage tone="error">{getErrorMessage(error)}</InlineMessage> : null}
        <TextField
          label={t('glossary:categoryForm.fields.name')}
          placeholder={t('glossary:categoryForm.fields.namePlaceholder')}
          value={draft.name}
          error={nameError}
          onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))}
        />
        <TextAreaField
          label={t('glossary:categoryForm.fields.description')}
          placeholder={t('glossary:categoryForm.fields.descriptionPlaceholder')}
          value={draft.description}
          onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))}
        />
      </div>
    </FormModal>
  );
}
