import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Button } from '@/shared/ui/Button';
import { FormModal } from '@/shared/ui/FormModal';
import { NumberField, SelectField, TextField, ToggleField } from '@/shared/ui/FormFields';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { JsonEditor } from '@/shared/ui/JsonEditor';
import type { LlmModelInstanceView, LlmModelInstanceWriteModel } from '../../lib/contracts';
import { useModelOptions } from '../../options/hooks';

import { emptyModelInstanceDraft, toModelInstanceDraft } from './types';

const emptyOptions: { modelKey: string; modelName: string; displayName: string; isEnabled: boolean }[] = [];

function validateDraft(
  mode: 'create' | 'edit',
  modelKey: string,
  draft: LlmModelInstanceWriteModel,
  apiKeyInput: string,
  t: (key: string) => string,
) {
  const errors: Record<string, string> = {};

  if (mode === 'create' && !modelKey.trim()) {
    errors.modelKey = t('modules.modelManagement.modelInstances.drawer.validation.modelKeyRequired');
  }

  if (!draft.instanceKey.trim()) {
    errors.instanceKey = t('modules.modelManagement.modelInstances.drawer.validation.instanceKeyRequired');
  }

  if (draft.priority < 0) {
    errors.priority = t('modules.modelManagement.modelInstances.drawer.validation.priorityMin');
  }

  if (draft.weight <= 0) {
    errors.weight = t('modules.modelManagement.modelInstances.drawer.validation.weightMin');
  }

  if (draft.defaultTimeoutMs <= 0) {
    errors.defaultTimeoutMs = t('modules.modelManagement.modelInstances.drawer.validation.timeoutMin');
  }

  if (mode === 'create' && !apiKeyInput.trim()) {
    errors.apiKey = t('modules.modelManagement.modelInstances.drawer.validation.apiKeyRequired');
  }

  return errors;
}

export function ModelInstanceDrawer({
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
  initialValue: LlmModelInstanceView | null;
  modelKeyPreset?: string;
  loading: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (payload: { modelKey: string; model: LlmModelInstanceWriteModel }) => Promise<void>;
}) {
  const { t } = useTranslation();
  const [modelKey, setModelKey] = useState(modelKeyPreset ?? '');
  const [draft, setDraft] = useState<LlmModelInstanceWriteModel>(emptyModelInstanceDraft);
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const modelOptionsQuery = useModelOptions(open);

  const cards = Array.isArray(modelOptionsQuery.data) ? modelOptionsQuery.data : emptyOptions;

  const modelOptions = useMemo(
    () =>
      cards.map((item) => ({
        value: item.modelKey,
        label: item.displayName,
      })),
    [cards],
  );

  useEffect(() => {
    setModelKey(modelKeyPreset ?? '');

    if (initialValue) {
      const { modelKey: initialModelKey, ...instanceDraft } = initialValue;
      setModelKey(modelKeyPreset ?? initialModelKey);
      setDraft({ ...instanceDraft, apiKey: null });
      setApiKeyInput('');
      return;
    }

    setDraft(emptyModelInstanceDraft);
    setApiKeyInput('');
  }, [initialValue, open, modelKeyPreset]);

  // Auto-fill providerDeploymentName when modelKeyPreset is set and model options are loaded
  useEffect(() => {
    if (mode === 'create' && modelKeyPreset && cards.length > 0) {
      const selected = cards.find((c) => c.modelKey === modelKeyPreset);
      if (selected) {
        setDraft((current) => ({ ...current, providerDeploymentName: selected.modelName }));
      }
    }
  }, [mode, modelKeyPreset, cards]);

  const errors = validateDraft(mode, modelKey, draft, apiKeyInput, t);
  const showCardSelector = mode === 'create' || Boolean(modelKeyPreset);
  const lockCardSelector = Boolean(modelKeyPreset);

  const handleSubmit = () => {
    onSubmit({
      modelKey,
      model: {
        ...toModelInstanceDraft(draft),
        apiKey: apiKeyInput.trim() || null,
      },
    });
  };

  return (
    <FormModal
      open={open}
      title={mode === 'create' ? t('modules.modelManagement.modelInstances.drawer.titleCreate') : t('modules.modelManagement.modelInstances.drawer.titleEdit')}
      description={t('modules.modelManagement.modelInstances.drawer.description')}
      onClose={onClose}
      widthClassName="max-w-4xl"
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose}>
            {t('modules.modelManagement.modelInstances.drawer.actions.cancel')}
          </Button>
          <Button onClick={handleSubmit} disabled={loading || Object.keys(errors).length > 0}>
            {loading
              ? t('modules.modelManagement.modelInstances.drawer.actions.submitting')
              : mode === 'create'
                ? t('modules.modelManagement.modelInstances.drawer.actions.create')
                : t('modules.modelManagement.modelInstances.drawer.actions.save')}
          </Button>
        </div>
      }
    >
      <div className="space-y-6">
        {error ? <InlineMessage tone="error">{error}</InlineMessage> : null}

        <div className="grid gap-4 md:grid-cols-2">
          {showCardSelector ? (
            <SelectField
               label={t('modules.modelManagement.modelInstances.drawer.fields.modelKey')}
              value={modelKey}
              error={errors.modelKey}
              disabled={lockCardSelector}
              onChange={(event) => {
                const value = event.target.value;
                setModelKey(value);
                const selected = cards.find((c) => c.modelKey === value);
                if (selected) {
                  setDraft((current) => ({ ...current, providerDeploymentName: selected.modelName }));
                }
              }}
            >
              <option value="">{modelOptionsQuery.isLoading ? t('modules.modelManagement.modelInstances.drawer.fields.modelKeyLoading') : t('modules.modelManagement.modelInstances.drawer.fields.modelKeyPlaceholder')}</option>
              {modelOptions.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label} ({item.value})
                </option>
              ))}
            </SelectField>
          ) : null}

          <TextField
             label={t('modules.modelManagement.modelInstances.drawer.fields.instanceKey')}
            value={draft.instanceKey}
            error={errors.instanceKey}
            onChange={(event) => setDraft((current) => ({ ...current, instanceKey: event.target.value }))}
          />

          <TextField
             label={t('modules.modelManagement.modelInstances.drawer.fields.deploymentName')}
            value={draft.providerDeploymentName ?? ''}
            onChange={(event) => setDraft((current) => ({ ...current, providerDeploymentName: event.target.value }))}
          />
        </div>

        <div className="space-y-4">
          <TextField
             label={t('modules.modelManagement.modelInstances.drawer.fields.apiKey')}
            type="password"
            value={apiKeyInput}
            error={errors.apiKey}
            onChange={(event) => setApiKeyInput(event.target.value)}
             hint={mode === 'edit' ? t('modules.modelManagement.modelInstances.drawer.fields.apiKeyHintEdit') : t('modules.modelManagement.modelInstances.drawer.fields.apiKeyHintCreate')}
             placeholder={mode === 'edit' ? t('modules.modelManagement.modelInstances.drawer.fields.apiKeyPlaceholderEdit') : undefined}
          />
        </div>

        {/* Advanced Options */}
        <div className="rounded-[2px] border border-border">
          <button
            type="button"
            className="flex w-full items-center gap-2 px-4 py-3 text-sm font-medium text-text-secondary hover:bg-surface/60"
            onClick={() => setAdvancedOpen((v) => !v)}
          >
            {advancedOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            {t('modules.modelManagement.modelInstances.drawer.fields.advancedOptions')}
          </button>
          {advancedOpen && (
            <div className="border-t border-border px-4 py-4">
              <div className="grid gap-4 md:grid-cols-2">
                <TextField
                   label={t('modules.modelManagement.modelInstances.drawer.fields.region')}
                  value={draft.region ?? ''}
                  onChange={(event) => setDraft((current) => ({ ...current, region: event.target.value }))}
                />

                <NumberField
                   label={t('modules.modelManagement.modelInstances.drawer.fields.priority')}
                  value={draft.priority}
                  error={errors.priority}
                  onChange={(event) => setDraft((current) => ({ ...current, priority: Number(event.target.value) }))}
                />

                <NumberField
                   label={t('modules.modelManagement.modelInstances.drawer.fields.weight')}
                  value={draft.weight}
                  error={errors.weight}
                  onChange={(event) => setDraft((current) => ({ ...current, weight: Number(event.target.value) }))}
                />

                <NumberField
                   label={t('modules.modelManagement.modelInstances.drawer.fields.timeout')}
                  value={draft.defaultTimeoutMs}
                  error={errors.defaultTimeoutMs}
                  onChange={(event) => setDraft((current) => ({ ...current, defaultTimeoutMs: Number(event.target.value) }))}
                />
              </div>
            </div>
          )}
        </div>

        <JsonEditor
          label={t('modules.modelManagement.modelInstances.drawer.fields.extraJson')}
          kind="object"
          value={typeof draft.extraJson === 'object' ? JSON.stringify(draft.extraJson, null, 2) : draft.extraJson}
          onChange={(value) => { try { setDraft((current) => ({ ...current, extraJson: value.trim() ? JSON.parse(value) : {} })); } catch { /* ignore parse errors while typing */ } }}
          hint={t('modules.modelManagement.modelInstances.drawer.fields.extraJsonHint')}
        />

        <div className="grid gap-4 md:grid-cols-2">
          <ToggleField
             label={t('modules.modelManagement.modelInstances.drawer.fields.isEnabled')}
            checked={draft.isEnabled}
            onChange={(checked) => setDraft((current) => ({ ...current, isEnabled: checked }))}
          />
          <ToggleField
             label={t('modules.modelManagement.modelInstances.drawer.fields.isHealthy')}
            checked={draft.isHealthy}
            onChange={(checked) => setDraft((current) => ({ ...current, isHealthy: checked }))}
          />
        </div>
      </div>
    </FormModal>
  );
}
