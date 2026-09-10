import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FormModal } from '@/shared/ui/FormModal';
import { Button } from '@/shared/ui/Button';
import { NumberField, SelectField, TextAreaField, TextField, ToggleField } from '@/shared/ui/FormFields';
import type { KbView } from '../../../lib/contracts';
import {
  createDefaultKbSettings,
  parseKbSettingsJson,
  serializeKbSettings,
  type KbSettingsFormState,
} from '../settings';

// Azure provider 与 Azure Chunk Push 已下线，新增/编辑固定使用 local 提供方。
const LOCAL_ONLY_SETTINGS = { provider: 'local' as const, recallSources: [] };

export function KbCreateDrawer({
  open,
  mode,
  initialValue,
  loading,
  onSubmit,
  onClose,
}: {
  open: boolean;
  mode: 'create' | 'edit';
  initialValue: KbView | null;
  loading: boolean;
  onSubmit: (data: { name: string; description?: string; settingsJson?: string }) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation(['common', 'knowledgeBase']);
  const [name, setName] = useState(initialValue?.name ?? '');
  const [description, setDescription] = useState(initialValue?.description ?? '');
  const [settings, setSettings] = useState<KbSettingsFormState>(() => ({
    ...parseKbSettingsJson(initialValue?.settingsJson),
    ...LOCAL_ONLY_SETTINGS,
  }));

  useEffect(() => {
    if (!open) {
      return;
    }

    setName(initialValue?.name ?? '');
    setDescription(initialValue?.description ?? '');
    setSettings({ ...parseKbSettingsJson(initialValue?.settingsJson), ...LOCAL_ONLY_SETTINGS });
  }, [initialValue, open]);

  const handleClose = () => {
    setName('');
    setDescription('');
    setSettings(createDefaultKbSettings());
    onClose();
  };

  const updateLocal = <T extends keyof KbSettingsFormState['local']>(
    key: T,
    value: KbSettingsFormState['local'][T],
  ) => {
    setSettings((current) => ({
      ...current,
      local: {
        ...current.local,
        [key]: value,
      },
    }));
  };

  const saveDisabled = loading || !name.trim();

  const handleSubmit = () => {
    if (saveDisabled) return;
    onSubmit({
      name: name.trim(),
      description: description.trim() || undefined,
      settingsJson: serializeKbSettings(settings),
    });
  };

  return (
    <FormModal
      open={open}
      title={mode === 'create' ? t('knowledgeBase:create.titleCreate') : t('knowledgeBase:create.titleEdit')}
      onClose={handleClose}
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={handleClose}>
            {t('common:actions.cancel')}
          </Button>
          <Button onClick={handleSubmit} disabled={saveDisabled}>
            {loading
              ? t('knowledgeBase:create.submitting')
              : mode === 'create'
                ? t('knowledgeBase:create.submitCreate')
                : t('knowledgeBase:create.submitEdit')}
          </Button>
        </div>
      }
    >
      <div className="space-y-5">
        <TextField
          label={t('knowledgeBase:create.nameLabel')}
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t('knowledgeBase:create.namePlaceholder')}
        />
        <TextAreaField
          label={t('knowledgeBase:create.descriptionLabel')}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder={t('knowledgeBase:create.descriptionPlaceholder')}
        />
        {/* Retrieval tuning stays out of the first screen: defaults work, and
            the product action is name -> create -> add content. */}
        <details className="rounded-[2px] border border-border bg-surface/70 p-4">
          <summary className="cursor-pointer text-sm font-medium text-text">
            {t('knowledgeBase:create.advancedTitle')}
          </summary>
          <p className="mt-2 text-xs text-text-muted">{t('knowledgeBase:create.advancedSummary')}</p>
          <div className="mt-4 space-y-4">
            <SelectField
              label={t('knowledgeBase:create.providerLabel')}
              disabled={mode === 'edit'}
              hint={mode === 'edit' ? t('knowledgeBase:create.providerLockedHint') : undefined}
              value={settings.provider}
              onChange={() => setSettings((current) => ({ ...current, ...LOCAL_ONLY_SETTINGS }))}
            >
              <option value="local">Local</option>
            </SelectField>

            <div className="grid gap-4 md:grid-cols-2">
              <NumberField
                label={t('knowledgeBase:create.chunkMaxLengthLabel')}
                min={1}
                value={String(settings.local.maxLength)}
                onChange={(e) => updateLocal('maxLength', Number(e.target.value || 0))}
              />
              <NumberField
                label={t('knowledgeBase:create.chunkOverlapLabel')}
                min={0}
                value={String(settings.local.overlap)}
                onChange={(e) => updateLocal('overlap', Number(e.target.value || 0))}
              />
            </div>
            <TextField
              label={t('knowledgeBase:create.splitterLabel')}
              value={settings.local.splitter}
              onChange={(e) => updateLocal('splitter', e.target.value)}
            />
            <div className="grid gap-3 md:grid-cols-2">
              <ToggleField
                label={t('knowledgeBase:create.embeddingIndexLabel')}
                hint={t('knowledgeBase:create.embeddingIndexHint')}
                checked={settings.local.indexes.includes('embedding')}
                onChange={(checked) =>
                  updateLocal(
                    'indexes',
                    checked
                      ? Array.from(new Set([...settings.local.indexes, 'embedding']))
                      : settings.local.indexes.filter((item) => item !== 'embedding'),
                  )
                }
              />
              <ToggleField
                label={t('knowledgeBase:create.fullTextIndexLabel')}
                hint={t('knowledgeBase:create.fullTextIndexHint')}
                checked={settings.local.indexes.includes('full_text')}
                onChange={(checked) =>
                  updateLocal(
                    'indexes',
                    checked
                      ? Array.from(new Set([...settings.local.indexes, 'full_text']))
                      : settings.local.indexes.filter((item) => item !== 'full_text'),
                  )
                }
              />
            </div>
          </div>
        </details>
      </div>
    </FormModal>
  );
}
