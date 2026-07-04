import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { valueTypeOptions } from '@/shared/config/catalogOptions';
import { Button } from '@/shared/ui/Button';
import { FormModal } from '@/shared/ui/FormModal';
import { SelectField, TextField, ToggleField } from '@/shared/ui/FormFields';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { JsonEditor } from '@/shared/ui/JsonEditor';
import type { LlmFeatureView, LlmFeatureWriteModel } from '../../lib/contracts';
import { emptyFeatureDraft, toFeatureDraft } from './types';

function validateDraft(_mode: 'create' | 'edit', draft: LlmFeatureWriteModel, t: (key: string) => string) {
  const errors: Partial<Record<keyof LlmFeatureWriteModel, string>> = {};

  if (!draft.featureKey.trim()) errors.featureKey = t('modules.modelManagement.featureDefinitions.drawer.validation.featureKeyRequired');
  if (!draft.displayName.trim()) errors.displayName = t('modules.modelManagement.featureDefinitions.drawer.validation.displayNameRequired');
  if (!draft.valueType.trim()) errors.valueType = t('modules.modelManagement.featureDefinitions.drawer.validation.valueTypeRequired');

  return errors;
}

export function FeatureDrawer({
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
  initialValue: LlmFeatureView | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (model: LlmFeatureWriteModel) => Promise<void>;
}) {
  const [draft, setDraft] = useState<LlmFeatureWriteModel>(emptyFeatureDraft);
  const [rawAllowedValuesJson, setRawAllowedValuesJson] = useState('[]');
  const { t } = useTranslation();

  useEffect(() => {
    setDraft(initialValue ?? emptyFeatureDraft);
    setRawAllowedValuesJson(
      initialValue?.allowedValuesJson && Array.isArray(initialValue.allowedValuesJson)
        ? JSON.stringify(initialValue.allowedValuesJson, null, 2)
        : '[]',
    );
  }, [initialValue, open]);

  // Debounce allowedValuesJson parse: only update draft 300ms after the user stops typing
  useEffect(() => {
    const timer = setTimeout(() => {
      try {
        const parsed = rawAllowedValuesJson.trim() ? JSON.parse(rawAllowedValuesJson) : [];
        setDraft((current) => {
          if (JSON.stringify(current.allowedValuesJson) === JSON.stringify(parsed)) return current;
          return { ...current, allowedValuesJson: parsed };
        });
      } catch {
        // ignore parse errors — user is still typing
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [rawAllowedValuesJson]);

  const validationErrors = validateDraft(mode, draft, t);

  return (
    <FormModal
      open={open}
      title={mode === 'create' ? t('modules.modelManagement.featureDefinitions.drawer.titleCreate') : t('modules.modelManagement.featureDefinitions.drawer.titleEdit')}
      description={t('modules.modelManagement.featureDefinitions.drawer.description')}
      onClose={onClose}
      widthClassName="max-w-4xl"
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose}>
            {t('modules.modelManagement.featureDefinitions.drawer.actions.cancel')}
          </Button>
          <Button
            onClick={() => onSubmit(toFeatureDraft(draft))}
            disabled={loading || Object.keys(validationErrors).length > 0}
          >
            {loading ? t('modules.modelManagement.featureDefinitions.drawer.actions.submitting') : mode === 'create' ? t('modules.modelManagement.featureDefinitions.drawer.actions.create') : t('modules.modelManagement.featureDefinitions.drawer.actions.save')}
          </Button>
        </div>
      }
    >
      <div className="space-y-5">
        {error ? <InlineMessage tone="error">{error}</InlineMessage> : null}
        <div className="grid gap-4 md:grid-cols-2">
          <TextField
          label={t('modules.modelManagement.featureDefinitions.drawer.fields.featureKey')}
            value={draft.featureKey}
            error={validationErrors.featureKey}
            disabled={mode === 'edit'}
            onChange={(event) => setDraft((current) => ({ ...current, featureKey: event.target.value }))}
          />
          <TextField
            label={t('modules.modelManagement.featureDefinitions.drawer.fields.displayName')}
            value={draft.displayName}
            error={validationErrors.displayName}
            onChange={(event) => setDraft((current) => ({ ...current, displayName: event.target.value }))}
          />
          <SelectField
            label={t('modules.modelManagement.featureDefinitions.drawer.fields.valueType')}
            value={draft.valueType}
            error={validationErrors.valueType}
            onChange={(event) => setDraft((current) => ({ ...current, valueType: event.target.value }))}
          >
            {valueTypeOptions.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </SelectField>
        </div>
        <TextField
          label={t('modules.modelManagement.featureDefinitions.drawer.fields.description')}
          value={draft.description ?? ''}
          onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))}
        />
        <JsonEditor
          label={t('modules.modelManagement.featureDefinitions.drawer.fields.allowedValues')}
          kind="array"
          value={rawAllowedValuesJson}
          onChange={(value) => {
            setRawAllowedValuesJson(value);
          }}
          hint={t('modules.modelManagement.featureDefinitions.drawer.fields.allowedValuesHint')}
        />
        <div className="grid gap-4 md:grid-cols-3">
          <ToggleField
            label={t('modules.modelManagement.featureDefinitions.drawer.fields.isFilterable')}
            checked={draft.isFilterable}
            onChange={(checked) => setDraft((current) => ({ ...current, isFilterable: checked }))}
          />
          <ToggleField
            label={t('modules.modelManagement.featureDefinitions.drawer.fields.isRoutable')}
            checked={draft.isRoutable}
            onChange={(checked) => setDraft((current) => ({ ...current, isRoutable: checked }))}
          />
          <ToggleField
            label={t('modules.modelManagement.featureDefinitions.drawer.fields.isEnabled')}
            checked={draft.isEnabled}
            onChange={(checked) => setDraft((current) => ({ ...current, isEnabled: checked }))}
          />
        </div>
      </div>
    </FormModal>
  );
}

// Backward-compatible re-export for route lazy loading
export { FeatureDrawer as FeatureDefinitionDrawer };
