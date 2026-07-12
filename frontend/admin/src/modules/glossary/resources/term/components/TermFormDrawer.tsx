import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getErrorMessage } from '@/shared/api/errors';
import { Button } from '@/shared/ui/Button';
import { FormModal } from '@/shared/ui/FormModal';
import { SelectField, TextAreaField, TextField } from '@/shared/ui/FormFields';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import type {
  GlossaryCategoryView,
  GlossaryTermCreateRequest,
  GlossaryTermUpdateRequest,
  GlossaryTermView,
} from '../../../lib/contracts';

type TermDraft = {
  categoryId: string;
  term: string;
  synonymsText: string;
};

const emptyDraft: TermDraft = {
  categoryId: '',
  term: '',
  synonymsText: '',
};

function serializeSynonyms(value: string[]) {
  return value.join('\n');
}

function parseSynonyms(value: string) {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean)
    .filter((item, index, collection) => collection.indexOf(item) === index);
}

function toDraft(value: GlossaryTermView | null | undefined, defaultCategoryId?: string): TermDraft {
  if (!value) {
    return {
      ...emptyDraft,
      categoryId: defaultCategoryId ?? '',
    };
  }

  return {
    categoryId: value.categoryId,
    term: value.term,
    synonymsText: serializeSynonyms(value.synonyms),
  };
}

export function TermFormDrawer({
  open,
  mode,
  categories,
  defaultCategoryId,
  defaultCategoryName,
  initialValue,
  loading,
  error,
  onClose,
  onSubmit,
}: {
  open: boolean;
  mode: 'create' | 'edit';
  categories: GlossaryCategoryView[];
  defaultCategoryId?: string;
  defaultCategoryName?: string;
  initialValue: GlossaryTermView | null;
  loading: boolean;
  error: unknown;
  onClose: () => void;
  onSubmit: (payload: GlossaryTermCreateRequest | GlossaryTermUpdateRequest) => void;
}) {
  const { t } = useTranslation(['common', 'glossary']);
  const [draft, setDraft] = useState<TermDraft>(toDraft(initialValue, defaultCategoryId));
  const showFixedCategory = Boolean(
    defaultCategoryId
    && defaultCategoryName
    && (!initialValue || !categories.some((category) => category.id === draft.categoryId)),
  );

  useEffect(() => {
    setDraft(toDraft(initialValue, defaultCategoryId));
  }, [defaultCategoryId, initialValue, open]);

  const validation = useMemo(
    () => ({
      categoryId: draft.categoryId ? null : t('glossary:termForm.validation.categoryRequired'),
      term: draft.term.trim() ? null : t('glossary:termForm.validation.termRequired'),
    }),
    [draft.categoryId, draft.term, t],
  );

  return (
    <FormModal
      open={open}
      title={mode === 'create' ? t('glossary:termForm.titleCreate') : t('glossary:termForm.titleEdit')}
      description={t('glossary:termForm.description')}
      onClose={onClose}
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose}>
            {t('glossary:termForm.actions.cancel')}
          </Button>
          <Button
            onClick={() =>
              onSubmit({
                categoryId: draft.categoryId,
                term: draft.term.trim(),
                synonyms: parseSynonyms(draft.synonymsText),
              })
            }
            disabled={loading || Boolean(validation.categoryId) || Boolean(validation.term)}
          >
            {loading
              ? t('glossary:termForm.actions.submitting')
              : mode === 'create'
                ? t('glossary:termForm.actions.create')
                : t('glossary:termForm.actions.save')}
          </Button>
        </div>
      }
    >
      <div className="space-y-5">
        {error ? <InlineMessage tone="error">{getErrorMessage(error)}</InlineMessage> : null}
        {showFixedCategory ? (
            <div className="space-y-2">
            <div className="text-sm font-medium text-text">{t('glossary:termForm.fields.category')}</div>
            <div className="rounded-[2px] border border-border-strong bg-background-subtle px-4 py-3 text-sm text-text">
              {defaultCategoryName}
            </div>
          </div>
        ) : (
            <SelectField
            label={t('glossary:termForm.fields.category')}
            value={draft.categoryId}
            error={validation.categoryId}
            onChange={(event) => setDraft((current) => ({ ...current, categoryId: event.target.value }))}
          >
            <option value="">{t('glossary:termForm.fields.categoryPlaceholder')}</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </SelectField>
        )}
        <TextField
          label={t('glossary:termForm.fields.term')}
          placeholder={t('glossary:termForm.fields.termPlaceholder')}
          value={draft.term}
          error={validation.term}
          onChange={(event) => setDraft((current) => ({ ...current, term: event.target.value }))}
        />
        <TextAreaField
          label={t('glossary:termForm.fields.synonyms')}
          hint={t('glossary:termForm.fields.synonymsHint')}
          placeholder={t('glossary:termForm.fields.synonymsPlaceholder')}
          value={draft.synonymsText}
          onChange={(event) => setDraft((current) => ({ ...current, synonymsText: event.target.value }))}
        />
      </div>
    </FormModal>
  );
}
