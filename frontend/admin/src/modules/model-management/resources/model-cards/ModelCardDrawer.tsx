import { useEffect, useState } from 'react';
import { Settings } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { capabilityOptions, getCapabilityLabel } from '@/shared/config/catalogOptions';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { FormModal } from '@/shared/ui/FormModal';
import { JsonEditor } from '@/shared/ui/JsonEditor';
import { SelectField, TextAreaField, TextField } from '@/shared/ui/FormFields';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import type { LlmModelView, LlmModelWriteModel } from '../../lib/contracts';
import { useConnectionProfileOptions, useFeatureOptions } from '../../options/hooks';
import { emptyModelDraft, toModelDraft } from './types';

function validateDraft(draft: LlmModelWriteModel, t: (key: string) => string) {
  const errors: Partial<Record<keyof LlmModelWriteModel, string>> = {};
  if (!draft.modelKey.trim()) errors.modelKey = t('modelManagement:models.drawer.validation.modelKeyRequired');
  if (!draft.modelName.trim()) errors.modelName = t('modelManagement:models.drawer.validation.modelNameRequired');
  if (!draft.displayName.trim()) errors.displayName = t('modelManagement:models.drawer.validation.displayNameRequired');
  if (!draft.connectionProfileKey.trim()) errors.connectionProfileKey = t('modelManagement:models.drawer.validation.connectionProfileKeyRequired');
  return errors;
}

export function ModelDrawer({
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
  initialValue: LlmModelView | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (model: LlmModelWriteModel, options: { navigateToDetail?: boolean }) => Promise<void>;
}) {
  const [draft, setDraft] = useState<LlmModelWriteModel>(emptyModelDraft);
  const [displayNameTouched, setDisplayNameTouched] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(true);
  const [featuresOpen, setFeaturesOpen] = useState(true);
  const [pricingOpen, setPricingOpen] = useState(false);
  const [navigateToDetailAfterCreate, setNavigateToDetailAfterCreate] = useState(true);
  const { t } = useTranslation(['common', 'modelManagement']);
  const featureOptionsQuery = useFeatureOptions(open);
  const connectionProfileOptionsQuery = useConnectionProfileOptions(open);
  const featureDefinitions = featureOptionsQuery.data ?? [];
  const connectionProfiles = connectionProfileOptionsQuery.data ?? [];

  useEffect(() => {
    if (initialValue) {
      setDraft({
        modelKey: initialValue.modelKey,
        type: initialValue.type,
        modelName: initialValue.modelName,
        displayName: initialValue.displayName,
        description: initialValue.description,
        connectionProfileKey: initialValue.connectionProfileKey,
        tagsJson: initialValue.tagsJson,
        routingPolicyJson: initialValue.routingPolicyJson,
        retryPolicyJson: initialValue.retryPolicyJson,
        isEnabled: initialValue.isEnabled,
        inputPricePerMtok: (initialValue as any).inputPricePerMtok,
        outputPricePerMtok: (initialValue as any).outputPricePerMtok,
        cacheWritePricePerMtok: (initialValue as any).cacheWritePricePerMtok,
        cacheReadPricePerMtok: (initialValue as any).cacheReadPricePerMtok,
      });
      setDisplayNameTouched(initialValue.displayName.trim() !== initialValue.modelName.trim());
      return;
    }

    setDraft(emptyModelDraft);
    setDisplayNameTouched(false);
    setNavigateToDetailAfterCreate(true);
  }, [initialValue, open]);

  const validationErrors = validateDraft(draft, t);

  return (
    <FormModal
      open={open}
      title={mode === 'create' ? t('modelManagement:models.drawer.titleCreate') : t('modelManagement:models.drawer.titleEdit')}
      onClose={onClose}
      widthClassName="max-w-4xl"
      footer={
        <div className="flex items-center justify-between">
          {mode === 'create' ? (
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="navigate-to-detail"
                checked={navigateToDetailAfterCreate}
                onChange={(e) => setNavigateToDetailAfterCreate(e.target.checked)}
                className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
              />
              <label htmlFor="navigate-to-detail" className="text-sm text-text-secondary">
                {t('modelManagement:models.drawer.navigateToDetail')}
              </label>
            </div>
          ) : (
            <div />
          )}
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={onClose}>
              {t('modelManagement:models.drawer.actions.cancel')}
            </Button>
            <Button
              onClick={() => onSubmit(toModelDraft(draft), { navigateToDetail: navigateToDetailAfterCreate })}
              disabled={loading || Object.keys(validationErrors).length > 0}
            >
              {loading ? t('modelManagement:models.drawer.actions.submitting') : mode === 'create' ? t('modelManagement:models.drawer.actions.create') : t('modelManagement:models.drawer.actions.save')}
            </Button>
          </div>
        </div>
      }
    >
      <div className="space-y-5">
        {error ? <InlineMessage tone="error">{error}</InlineMessage> : null}
        <div className="grid gap-4 md:grid-cols-2">
          <TextField label={t('modelManagement:models.drawer.fields.modelKey')} value={draft.modelKey} error={validationErrors.modelKey} onChange={(event) => setDraft((current) => ({ ...current, modelKey: event.target.value }))} />
          <SelectField
            label={t('modelManagement:models.drawer.fields.type')}
            value={draft.type}
            onChange={(event) => setDraft((current) => ({ ...current, type: event.target.value as LlmModelWriteModel['type'] }))}
          >
            {capabilityOptions.map((item) => (
              <option key={item.value} value={item.value}>
                {getCapabilityLabel(t, item.value)}
              </option>
            ))}
          </SelectField>
          <TextField
            label={t('modelManagement:models.drawer.fields.modelName')}
            value={draft.modelName}
            error={validationErrors.modelName}
            onChange={(event) =>
              setDraft((current) => {
                const modelName = event.target.value;
                const shouldSyncDisplayName = !displayNameTouched
                  || !current.displayName.trim()
                  || current.displayName === current.modelName;

                return {
                  ...current,
                  modelName,
                  displayName: shouldSyncDisplayName ? modelName : current.displayName,
                };
              })
            }
          />
          <TextField
            label={t('modelManagement:models.drawer.fields.displayName')}
            value={draft.displayName}
            error={validationErrors.displayName}
            onChange={(event) => {
              const displayName = event.target.value;
              setDisplayNameTouched(displayName.trim() !== draft.modelName.trim());
              setDraft((current) => ({ ...current, displayName }));
            }}
          />
          <SelectField label={t('modelManagement:models.drawer.fields.enableStatus')} value={draft.isEnabled ? 'true' : 'false'} onChange={(event) => setDraft((current) => ({ ...current, isEnabled: event.target.value === 'true' }))}>
            <option value="true">{t('modelManagement:models.drawer.fields.enabled')}</option>
            <option value="false">{t('modelManagement:models.drawer.fields.disabled')}</option>
          </SelectField>
          <SelectField
            label={t('modelManagement:models.drawer.fields.connectionProfileKey')}
            value={draft.connectionProfileKey}
            error={validationErrors.connectionProfileKey}
            onChange={(event) => setDraft((current) => ({ ...current, connectionProfileKey: event.target.value }))}
          >
            <option value="">{connectionProfileOptionsQuery.isLoading ? t('modelManagement:models.drawer.fields.connectionProfileLoading') : t('modelManagement:models.drawer.fields.connectionProfilePlaceholder')}</option>
            {connectionProfiles.map((item) => (
              <option key={item.profileKey} value={item.profileKey}>
                {item.displayName} ({item.profileKey})
              </option>
            ))}
          </SelectField>
        </div>
        <TextAreaField label={t('modelManagement:models.drawer.fields.description')} value={draft.description ?? ''} onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))} />

        <div className="rounded-[2px] border border-border bg-surface">
          <button type="button" className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-text" onClick={() => setPricingOpen((current) => !current)}>
            <div className="flex items-center gap-2">
              <Settings size={16} />
              <span>{t('modelManagement:models.drawer.pricing.sectionTitle')}</span>
            </div>
            <span className="text-text-muted">{pricingOpen ? t('modelManagement:connectionProfiles.drawer.advanced.collapse') : t('modelManagement:connectionProfiles.drawer.advanced.expand')}</span>
          </button>
          {pricingOpen ? (
            <div className="grid gap-4 border-t border-border p-4 md:grid-cols-2">
              <TextField
                label={t('modelManagement:models.drawer.pricing.inputPrice') + ' (' + t('modelManagement:models.drawer.pricing.unitHint') + ')'}
                type="number"
                placeholder="0.00"
                value={draft.inputPricePerMtok ?? ''}
                onChange={(event) => {
                  const val = event.target.value;
                  setDraft((current) => ({ ...current, inputPricePerMtok: val === '' ? undefined : parseFloat(val) }));
                }}
              />
              <TextField
                label={t('modelManagement:models.drawer.pricing.outputPrice') + ' (' + t('modelManagement:models.drawer.pricing.unitHint') + ')'}
                type="number"
                placeholder="0.00"
                value={draft.outputPricePerMtok ?? ''}
                onChange={(event) => {
                  const val = event.target.value;
                  setDraft((current) => ({ ...current, outputPricePerMtok: val === '' ? undefined : parseFloat(val) }));
                }}
              />
              <TextField
                label={t('modelManagement:models.drawer.pricing.cacheWritePrice') + ' (' + t('modelManagement:models.drawer.pricing.unitHint') + ')'}
                type="number"
                placeholder="0.00"
                value={draft.cacheWritePricePerMtok ?? ''}
                onChange={(event) => {
                  const val = event.target.value;
                  setDraft((current) => ({ ...current, cacheWritePricePerMtok: val === '' ? undefined : parseFloat(val) }));
                }}
              />
              <TextField
                label={t('modelManagement:models.drawer.pricing.cacheReadPrice') + ' (' + t('modelManagement:models.drawer.pricing.unitHint') + ')'}
                type="number"
                placeholder="0.00"
                value={draft.cacheReadPricePerMtok ?? ''}
                onChange={(event) => {
                  const val = event.target.value;
                  setDraft((current) => ({ ...current, cacheReadPricePerMtok: val === '' ? undefined : parseFloat(val) }));
                }}
              />
            </div>
          ) : null}
        </div>

        <div className="rounded-[2px] border border-border bg-surface">
          <button type="button" className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-text" onClick={() => setFeaturesOpen((current) => !current)}>
            <div className="flex items-center gap-2">
              <Settings size={16} />
              <span>{t('modelManagement:models.drawer.features.sectionTitle')}</span>
            </div>
            <span className="text-text-muted">{featuresOpen ? t('modelManagement:connectionProfiles.drawer.advanced.collapse') : t('modelManagement:connectionProfiles.drawer.advanced.expand')}</span>
          </button>
          {featuresOpen ? (
            <div className="border-t border-border p-4">
              {featureDefinitions.length > 0 ? (
                <div className="space-y-2">
                  <p className="text-xs text-text-muted">
                    {t('modelManagement:models.drawer.features.hint')}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {featureDefinitions.map((feature) => (
                      <Badge
                        key={feature.featureKey}
                        tone={feature.isEnabled ? 'neutral' : 'warning'}
                      >
                        {feature.displayName}
                        {!feature.isEnabled ? t('modelManagement:models.drawer.fields.disabledBadge') : ''}
                      </Badge>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-text-muted">
                {featureOptionsQuery.isLoading ? t('modelManagement:models.drawer.features.loading') : t('modelManagement:models.drawer.features.empty')}
                </p>
              )}
            </div>
          ) : null}
        </div>

        <div className="rounded-[2px] border border-border bg-surface">
          <button type="button" className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-text" onClick={() => setAdvancedOpen((current) => !current)}>
            <span>{t('modelManagement:models.drawer.advanced.sectionTitle')}</span>
            <span className="text-text-muted">{advancedOpen ? t('modelManagement:connectionProfiles.drawer.advanced.collapse') : t('modelManagement:connectionProfiles.drawer.advanced.expand')}</span>
          </button>
          {advancedOpen ? (
            <div className="grid gap-4 border-t border-border p-4">
              <JsonEditor label={t('modelManagement:models.drawer.advanced.tags')} kind="array" value={typeof draft.tagsJson === 'object' ? JSON.stringify(draft.tagsJson, null, 2) : draft.tagsJson} onChange={(value) => { try { setDraft((current) => ({ ...current, tagsJson: value.trim() ? JSON.parse(value) : [] })); } catch { /* ignore parse errors while typing */ } }} hint={t('modelManagement:models.drawer.advanced.tagsHint')} />
              <JsonEditor label={t('modelManagement:models.drawer.advanced.routingPolicy')} kind="object" value={typeof draft.routingPolicyJson === 'object' ? JSON.stringify(draft.routingPolicyJson, null, 2) : draft.routingPolicyJson} onChange={(value) => { try { setDraft((current) => ({ ...current, routingPolicyJson: value.trim() ? JSON.parse(value) : {} })); } catch { /* ignore parse errors while typing */ } }} hint={t('modelManagement:models.drawer.advanced.routingPolicyHint')} />
              <JsonEditor label={t('modelManagement:models.drawer.advanced.retryPolicy')} kind="object" value={typeof draft.retryPolicyJson === 'object' ? JSON.stringify(draft.retryPolicyJson, null, 2) : draft.retryPolicyJson} onChange={(value) => { try { setDraft((current) => ({ ...current, retryPolicyJson: value.trim() ? JSON.parse(value) : {} })); } catch { /* ignore parse errors while typing */ } }} hint={t('modelManagement:models.drawer.advanced.retryPolicyHint')} />
            </div>
          ) : null}
        </div>
      </div>
    </FormModal>
  );
}
