import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { capabilityOptions, getCapabilityLabel } from '@/shared/config/catalogOptions';
import { Button } from '@/shared/ui/Button';
import { FormModal } from '@/shared/ui/FormModal';
import { SelectField, TextField, ToggleField } from '@/shared/ui/FormFields';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import type { LlmModelBindingView, LlmModelBindingWriteModel } from '../../lib/contracts';
import { useModelOptions } from '../../options/hooks';
import { emptyModelBindingDraft } from './types';

function validateDraft(draft: LlmModelBindingWriteModel, t: (key: string) => string) {
  const errors: Partial<Record<keyof LlmModelBindingWriteModel, string>> = {};
  if (!draft.bindingKey.trim()) errors.bindingKey = t('modelManagement:modelBindings.drawer.validation.bindingKeyRequired');
  if (!draft.displayName.trim()) errors.displayName = t('modelManagement:modelBindings.drawer.validation.displayNameRequired');
  if (!draft.modelKey.trim()) errors.modelKey = t('modelManagement:modelBindings.drawer.validation.modelKeyRequired');
  return errors;
}

export function ModelBindingDrawer({
  open,
  mode,
  initialValue,
  modelKeyPreset,
  loading,
  error,
  onClose,
  onSubmit,
}: {
  open: boolean;
  mode: 'create' | 'edit';
  initialValue: LlmModelBindingView | null;
  modelKeyPreset?: string;
  loading: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (model: LlmModelBindingWriteModel) => Promise<void>;
}) {
  const [draft, setDraft] = useState<LlmModelBindingWriteModel>(emptyModelBindingDraft);
  const displayNameTouched = useRef(false);
  const { t } = useTranslation(['common', 'modelManagement']);
  const modelOptionsQuery = useModelOptions(open);
  const modelOptions = modelOptionsQuery.data ?? [];

  useEffect(() => {
    if (initialValue) {
      setDraft(initialValue);
      return;
    }

    setDraft({ ...emptyModelBindingDraft, modelKey: modelKeyPreset ?? '' });
    displayNameTouched.current = false;
  }, [initialValue, open, modelKeyPreset]);

  const errors = validateDraft(draft, t);

  return (
    <FormModal
      open={open}
      title={mode === 'create' ? t('modelManagement:modelBindings.drawer.titleCreate') : t('modelManagement:modelBindings.drawer.titleEdit')}
      description={t('modelManagement:modelBindings.drawer.description')}
      onClose={onClose}
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose}>
            {t('modelManagement:modelBindings.drawer.actions.cancel')}
          </Button>
          <Button onClick={() => onSubmit(draft)} disabled={loading || Object.keys(errors).length > 0}>
            {loading
              ? t('modelManagement:modelBindings.drawer.actions.submitting')
              : mode === 'create'
                ? t('modelManagement:modelBindings.drawer.actions.create')
                : t('modelManagement:modelBindings.drawer.actions.save')}
          </Button>
        </div>
      }
    >
      <div className="space-y-5">
        {error ? <InlineMessage tone="error">{error}</InlineMessage> : null}
        <div className="grid gap-4 md:grid-cols-2">
          <TextField label={t('modelManagement:modelBindings.drawer.fields.bindingKey')} value={draft.bindingKey} error={errors.bindingKey} onChange={(event) => {
            const next = event.target.value;
            setDraft((current) => ({
              ...current,
              bindingKey: next,
              displayName: displayNameTouched.current ? current.displayName : next,
            }));
          }} />
          <TextField label={t('modelManagement:modelBindings.drawer.fields.displayName')} value={draft.displayName} error={errors.displayName} onChange={(event) => {
            displayNameTouched.current = true;
            setDraft((current) => ({ ...current, displayName: event.target.value }));
          }} />
          <SelectField label={t('modelManagement:modelBindings.drawer.fields.capability')} value={draft.capability} onChange={(event) => setDraft((current) => ({ ...current, capability: event.target.value as LlmModelBindingWriteModel['capability'] }))}>
            {capabilityOptions.map((item) => (
              <option key={item.value} value={item.value}>
                {getCapabilityLabel(t, item.value)}
              </option>
            ))}
          </SelectField>
          <SelectField
            label={t('modelManagement:modelBindings.drawer.fields.modelKey')}
            value={draft.modelKey}
            error={errors.modelKey}
            disabled={Boolean(modelKeyPreset)}
            onChange={(event) => setDraft((current) => ({ ...current, modelKey: event.target.value }))}
          >
            <option value="">{modelOptionsQuery.isLoading ? t('modelManagement:modelBindings.drawer.fields.modelKeyLoading') : t('modelManagement:modelBindings.drawer.fields.modelKeyPlaceholder')}</option>
            {modelOptions.map((item) => (
              <option key={item.modelKey} value={item.modelKey}>
                {item.displayName} ({item.modelKey})
              </option>
            ))}
          </SelectField>
        </div>
        <ToggleField label={t('modelManagement:modelBindings.drawer.fields.enableBinding')} checked={draft.isEnabled} onChange={(checked) => setDraft((current) => ({ ...current, isEnabled: checked }))} />
      </div>
    </FormModal>
  );
}
