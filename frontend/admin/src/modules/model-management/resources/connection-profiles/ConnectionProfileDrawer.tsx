import { useEffect, useRef, useState } from 'react';
import { HelpCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { providerOptions } from '@/shared/config/catalogOptions';
import { Button } from '@/shared/ui/Button';
import { FormModal } from '@/shared/ui/FormModal';
import { SelectField, TextField, ToggleField } from '@/shared/ui/FormFields';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { JsonEditor } from '@/shared/ui/JsonEditor';
import type { LlmConnectionProfileView, LlmConnectionProfileWriteModel } from '../../lib/contracts';
import { emptyConnectionProfileDraft, toConnectionProfileDraft } from './types';

function HintTooltip({ content }: { content: string }) {
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const iconRef = useRef<HTMLSpanElement>(null);

  const show = () => {
    if (!iconRef.current) return;
    const rect = iconRef.current.getBoundingClientRect();
    setPos({ top: rect.bottom + 8, left: Math.max(12, Math.min(rect.left, window.innerWidth - 300)) });
  };

  return (
    <span ref={iconRef} className="inline-flex cursor-help" onMouseEnter={show} onMouseLeave={() => setPos(null)}>
      <HelpCircle size={14} className={`text-text-muted transition ${pos ? 'text-primary' : ''}`} />
      {pos ? (
        <span
          style={{ top: pos.top, left: pos.left }}
          className="fixed z-[200] w-72 rounded-[2px] border border-border bg-surface px-3.5 py-2.5 text-xs leading-relaxed text-text-secondary"
        >
          {content}
        </span>
      ) : null}
    </span>
  );
}

function validateDraft(draft: LlmConnectionProfileWriteModel, t: (key: string) => string) {
  const errors: Partial<Record<keyof LlmConnectionProfileWriteModel, string>> = {};

  if (!draft.profileKey.trim()) errors.profileKey = t('modules.modelManagement.connectionProfiles.drawer.validation.profileKeyRequired');
  if (!draft.displayName.trim()) errors.displayName = t('modules.modelManagement.connectionProfiles.drawer.validation.displayNameRequired');

  return errors;
}

export function ConnectionProfileDrawer({
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
  initialValue: LlmConnectionProfileView | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (model: LlmConnectionProfileWriteModel) => Promise<void>;
}) {
  const [draft, setDraft] = useState<LlmConnectionProfileWriteModel>(emptyConnectionProfileDraft);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [rawExtraJson, setRawExtraJson] = useState('{}');
  const { t } = useTranslation();

  useEffect(() => {
    setDraft(initialValue ?? emptyConnectionProfileDraft);
    setRawExtraJson(
      initialValue?.extraJson && typeof initialValue.extraJson === 'object'
        ? JSON.stringify(initialValue.extraJson, null, 2)
        : '{}',
    );
  }, [initialValue, open]);

  // Debounce extraJson parse: only update draft 300ms after the user stops typing
  useEffect(() => {
    const timer = setTimeout(() => {
      try {
        const parsed = rawExtraJson.trim() ? JSON.parse(rawExtraJson) : {};
        setDraft((current) => {
          if (JSON.stringify(current.extraJson) === JSON.stringify(parsed)) return current;
          return { ...current, extraJson: parsed };
        });
      } catch {
        // ignore parse errors — user is still typing
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [rawExtraJson]);

  const validationErrors = validateDraft(draft, t);

  return (
    <FormModal
      open={open}
      title={mode === 'create' ? t('modules.modelManagement.connectionProfiles.drawer.titleCreate') : t('modules.modelManagement.connectionProfiles.drawer.titleEdit')}
      description={t('modules.modelManagement.connectionProfiles.drawer.description')}
      onClose={onClose}
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose}>
            {t('modules.modelManagement.connectionProfiles.drawer.actions.cancel')}
          </Button>
          <Button
            onClick={() => onSubmit(toConnectionProfileDraft(draft))}
            disabled={loading || Object.keys(validationErrors).length > 0}
          >
            {loading ? t('modules.modelManagement.connectionProfiles.drawer.actions.submitting') : mode === 'create' ? t('modules.modelManagement.connectionProfiles.drawer.actions.create') : t('modules.modelManagement.connectionProfiles.drawer.actions.save')}
          </Button>
        </div>
      }
    >
      <div className="space-y-5">
        {error ? <InlineMessage tone="error">{error}</InlineMessage> : null}
        <div className="grid gap-4 md:grid-cols-2">
          <TextField
            label={t('modules.modelManagement.connectionProfiles.drawer.fields.profileKey')}
            value={draft.profileKey}
            error={validationErrors.profileKey}
            onChange={(event) => setDraft((current) => ({ ...current, profileKey: event.target.value }))}
          />
          <TextField
            label={t('modules.modelManagement.connectionProfiles.drawer.fields.displayName')}
            value={draft.displayName}
            error={validationErrors.displayName}
            onChange={(event) => setDraft((current) => ({ ...current, displayName: event.target.value }))}
          />
          <SelectField
            label="Provider"
            value={draft.provider}
            onChange={(event) => setDraft((current) => ({ ...current, provider: event.target.value as LlmConnectionProfileWriteModel['provider'] }))}
          >
            {providerOptions.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </SelectField>
          <TextField
            label={t('modules.modelManagement.connectionProfiles.drawer.fields.baseUrl')}
            labelSuffix={
              <HintTooltip content={t('modules.modelManagement.connectionProfiles.drawer.fields.baseUrlHint')} />
            }
            value={draft.baseUrl ?? ''}
            placeholder="https://api.openai.com/v1/"
            onChange={(event) => setDraft((current) => ({ ...current, baseUrl: event.target.value }))}
          />
          <TextField
            label={t('modules.modelManagement.connectionProfiles.drawer.fields.wsUrl')}
            labelSuffix={
              <HintTooltip content={t('modules.modelManagement.connectionProfiles.drawer.fields.wsUrlHint')} />
            }
            value={draft.webSocketBaseUrl ?? ''}
            onChange={(event) => setDraft((current) => ({ ...current, webSocketBaseUrl: event.target.value }))}
          />
          <TextField
            label={t('modules.modelManagement.connectionProfiles.drawer.fields.apiVersion')}
            labelSuffix={
              <HintTooltip content={t('modules.modelManagement.connectionProfiles.drawer.fields.apiVersionHint')} />
            }
            value={draft.apiVersion ?? ''}
            placeholder={t('modules.modelManagement.connectionProfiles.drawer.fields.apiVersionPlaceholder')}
            onChange={(event) => setDraft((current) => ({ ...current, apiVersion: event.target.value }))}
          />
          <TextField label="Region" value={draft.region ?? ''} onChange={(event) => setDraft((current) => ({ ...current, region: event.target.value }))} />
        </div>
        <ToggleField label={t('modules.modelManagement.connectionProfiles.drawer.fields.enableConnection')} checked={draft.isEnabled} onChange={(checked) => setDraft((current) => ({ ...current, isEnabled: checked }))} />
        <div className="rounded-[2px] border border-border bg-surface">
          <button
            type="button"
            className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-text"
            onClick={() => setAdvancedOpen((current) => !current)}
          >
            <span>{t('modules.modelManagement.connectionProfiles.drawer.advanced.sectionTitle')}</span>
            <span className="text-text-muted">{advancedOpen ? t('modules.modelManagement.connectionProfiles.drawer.advanced.collapse') : t('modules.modelManagement.connectionProfiles.drawer.advanced.expand')}</span>
          </button>
          {advancedOpen ? (
            <div className="border-t border-border p-4">
              <JsonEditor
                label={t('modules.modelManagement.connectionProfiles.drawer.fields.extraJson')}
                kind="object"
                value={rawExtraJson}
                onChange={(value) => {
                  setRawExtraJson(value);
                }}
                hint={t('modules.modelManagement.connectionProfiles.drawer.fields.extraJsonHint')}
              />
            </div>
          ) : null}
        </div>
      </div>
    </FormModal>
  );
}
