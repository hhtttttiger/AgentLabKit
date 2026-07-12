import { useMemo, useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/shared/lib/cn';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { Card } from '@/shared/ui/Card';
import { EmptyState } from '@/shared/ui/EmptyState';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { NumberField, SelectField, TextField } from '@/shared/ui/FormFields';
import type { LlmModelView } from '../../lib/contracts';
import {
  CardFeatureBadges,
  getDefaultFeatureInput,
  parseAllowedValues,
  toFeatureValueInput,
  toFeatureValueJson,
  validateFeatureValueInput,
} from '../../lib/features';
import {
  useFeatureEditorDrafts,
  type EditableFeature,
  type FeatureEditorDraft,
} from '../../lib/useFeatureEditorDrafts';

function InlineToggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      aria-pressed={checked}
      onClick={() => onChange(!checked)}
      className={cn(
        'relative h-6 w-10 shrink-0 rounded-full transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-state-focus/30',
        checked ? 'bg-primary' : 'bg-border-strong',
      )}
    >
      <span className={cn('absolute top-0.5 h-5 w-5 rounded-full bg-surface transition', checked ? 'left-[18px]' : 'left-0.5')} />
    </button>
  );
}

function InlineValueEditor({
  feature,
  draft,
  valueError,
  onUpdate,
}: {
  feature: EditableFeature;
  draft: FeatureEditorDraft;
  valueError: string | null;
  onUpdate: (valueInput: string) => void;
}) {
  const { t } = useTranslation(['common', 'modelManagement']);
  const allowedValues = parseAllowedValues(feature.allowedValuesJson);

  if (!draft.isSupported) {
    return <span className="text-xs text-text-muted">{t('modelManagement:models.featureSection.disabled')}</span>;
  }

  if (feature.valueType === 'boolean') {
    return (
      <InlineToggle
        checked={draft.valueInput === 'true'}
        onChange={(checked) => onUpdate(checked ? 'true' : 'false')}
      />
    );
  }

  if (feature.valueType === 'enum' && allowedValues.length) {
    return (
      <SelectField
        label=""
        value={draft.valueInput}
        error={valueError}
        fieldSize="compact"
        onChange={(event) => onUpdate(event.target.value)}
      >
        {allowedValues.map((item) => (
          <option key={item} value={item}>{item}</option>
        ))}
      </SelectField>
    );
  }

  if (feature.valueType === 'int' || feature.valueType === 'number') {
    return (
      <NumberField
        label=""
        value={draft.valueInput}
        error={valueError}
        fieldSize="compact"
        step={feature.valueType === 'int' ? 1 : 'any'}
        onChange={(event) => onUpdate(event.target.value)}
      />
    );
  }

  return (
    <TextField
      label=""
      value={draft.valueInput}
      error={valueError}
      fieldSize="compact"
      onChange={(event) => onUpdate(event.target.value)}
    />
  );
}

function FeatureRow({
  feature,
  draft,
  busy,
  isSaving,
  isRemoving,
  onUpdateDraft,
  onSave,
  onDelete,
}: {
  feature: EditableFeature;
  draft: FeatureEditorDraft;
  busy: boolean;
  isSaving: boolean;
  isRemoving: boolean;
  onUpdateDraft: (updater: (current: FeatureEditorDraft) => FeatureEditorDraft) => void;
  onSave: () => void;
  onDelete: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const { t } = useTranslation(['common', 'modelManagement']);

  const rawValueError = draft.isSupported
    ? validateFeatureValueInput(
        { valueType: feature.valueType, allowedValuesJson: feature.allowedValuesJson },
        draft.valueInput,
      )
    : null;
  const valueError = rawValueError ? t(rawValueError) : null;

  return (
    <div
      className={`rounded-[2px] border transition-colors ${
        draft.hasExisting
          ? 'border-l-[3px] border-l-primary/50 border-t-border border-r-border border-b-border bg-surface/80'
          : 'border-border bg-surface/40'
      }`}
    >
      {/* Main row */}
      <div className="flex items-center gap-3 px-4 py-3">
        <InlineToggle
          checked={draft.isSupported}
          onChange={(checked) => onUpdateDraft((current) => ({ ...current, isSupported: checked }))}
        />

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className={`text-sm font-medium ${draft.isSupported ? 'text-text' : 'text-text-muted line-through'}`}>
              {feature.displayName}
            </span>
            {feature.isFilterable ? <Badge>{t('modelManagement:models.featureSection.filterable')}</Badge> : null}
            {feature.isRoutable ? <Badge tone="success">{t('modelManagement:models.featureSection.routable')}</Badge> : null}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="w-36">
            <InlineValueEditor
              feature={feature}
              draft={draft}
              valueError={valueError}
              onUpdate={(valueInput) => onUpdateDraft((current) => ({ ...current, valueInput }))}
            />
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              onClick={onSave}
              disabled={busy || Boolean(valueError)}
            >
              {busy && isSaving ? t('modelManagement:models.featureSection.saving') : t('modelManagement:models.featureSection.save')}
            </Button>

            <button
              type="button"
              onClick={() => setExpanded(!expanded)}
              className={`rounded-lg p-1.5 text-text-muted transition hover:bg-background-subtle hover:text-text ${expanded ? 'rotate-180' : ''}`}
            >
              <ChevronDown size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Expandable detail */}
      {expanded ? (
        <div className="border-t border-border-subtle px-4 pb-3 pt-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <TextField
              label={t('modelManagement:models.featureSection.source')}
              value={draft.source}
              fieldSize="compact"
              onChange={(event) => onUpdateDraft((current) => ({ ...current, source: event.target.value }))}
            />
            <TextField
              label={t('modelManagement:models.featureSection.remark')}
              value={draft.remark}
              fieldSize="compact"
              onChange={(event) => onUpdateDraft((current) => ({ ...current, remark: event.target.value }))}
            />
          </div>
          {draft.hasExisting ? (
            <div className="mt-3 flex items-center justify-between">
              <span className="text-xs text-text-muted">{feature.featureKey} · {feature.valueType}</span>
              <Button variant="ghost" onClick={onDelete} disabled={busy}>
                {busy && isRemoving ? t('modelManagement:models.featureSection.removing') : t('modelManagement:models.featureSection.remove')}
              </Button>
            </div>
          ) : (
            <div className="mt-2 text-xs text-text-muted">{feature.featureKey} · {feature.valueType}</div>
          )}
        </div>
      ) : null}
    </div>
  );
}

export function ModelFeatureSection({
  modelKey,
  features,
}: {
  modelKey: string;
  features: LlmModelView['features'];
}) {
  const { t } = useTranslation(['common', 'modelManagement']);
  const {
    featureDefinitionsQuery,
    featureMutations,
    editableFeatures,
    featureDrafts,
    updateFeatureDraft,
    featureActionError,
    setFeatureActionError,
    activeFeatureKey,
    setActiveFeatureKey,
  } = useFeatureEditorDrafts(modelKey, features ?? []);

  const { configured, unconfigured } = useMemo(() => {
    const configuredItems: EditableFeature[] = [];
    const unconfiguredItems: EditableFeature[] = [];
    const currentFeatures = new Set((features ?? []).map((item) => item.featureKey));

    for (const item of editableFeatures) {
      if (currentFeatures.has(item.featureKey)) {
        configuredItems.push(item);
      } else {
        unconfiguredItems.push(item);
      }
    }

    return { configured: configuredItems, unconfigured: unconfiguredItems };
  }, [editableFeatures, features]);

  const handleSaveFeature = async (featureKey: string) => {
    const definition = editableFeatures.find((item) => item.featureKey === featureKey);
    const draftItem = featureDrafts[featureKey];
    if (!definition || !draftItem) {
      return;
    }

    setFeatureActionError(null);
    setActiveFeatureKey(featureKey);

    try {
      const nextValueJson = draftItem.isSupported
        ? toFeatureValueJson({ valueType: definition.valueType, allowedValuesJson: definition.allowedValuesJson }, draftItem.valueInput)
        : null;

      const saved = await featureMutations.upsert.mutateAsync({
        modelKey,
        featureKey,
        model: {
          featureKey,
          isSupported: draftItem.isSupported,
          valueJson: nextValueJson,
          source: draftItem.source.trim() || 'manual',
          remark: draftItem.remark.trim() || null,
        },
      });

      updateFeatureDraft(featureKey, (current) => ({
        ...current,
        hasExisting: true,
        isSupported: saved.isSupported,
        valueInput: toFeatureValueInput(saved.valueType, saved.valueJson, saved.allowedValuesJson),
        source: saved.source,
        remark: saved.remark ?? '',
      }));
    } catch (mutationError) {
      setFeatureActionError(featureMutations.getMutationMessage(mutationError));
    } finally {
      setActiveFeatureKey(null);
    }
  };

  const handleDeleteFeature = async (featureKey: string) => {
    const definition = editableFeatures.find((item) => item.featureKey === featureKey);
    if (!definition) {
      return;
    }

    setFeatureActionError(null);
    setActiveFeatureKey(featureKey);

    try {
      await featureMutations.remove.mutateAsync({
        modelKey,
        featureKey,
      });

      updateFeatureDraft(featureKey, (current) => ({
        ...current,
        hasExisting: false,
        isSupported: true,
        valueInput: getDefaultFeatureInput(definition),
        source: 'manual',
        remark: '',
      }));
    } catch (mutationError) {
      setFeatureActionError(featureMutations.getMutationMessage(mutationError));
    } finally {
      setActiveFeatureKey(null);
    }
  };

  const configuredCount = configured.length;
  const totalCount = editableFeatures.length;

  return (
    <Card
      title={t('modelManagement:models.featureSection.cardTitle')}
      description={totalCount > 0 ? t('modelManagement:models.featureSection.configuredCount', { configured: configuredCount, total: totalCount }) : undefined}
    >
      <div className="space-y-3">
        <CardFeatureBadges features={features} limit={8} />
        {featureActionError ? <InlineMessage tone="error">{featureActionError}</InlineMessage> : null}
        {featureDefinitionsQuery.isLoading ? <div className="text-sm text-text-secondary">{t('modelManagement:models.featureSection.loading')}</div> : null}

        {configured.length > 0 ? (
          <div className="space-y-2">
            <div className="text-xs font-medium tracking-wide text-text-muted">{t('modelManagement:models.featureSection.configured')}</div>
            {configured.map((feature) => {
              const featureDraft = featureDrafts[feature.featureKey];
              if (!featureDraft) return null;
              const busy = activeFeatureKey === feature.featureKey && (featureMutations.upsert.isPending || featureMutations.remove.isPending);
              return (
                <FeatureRow
                  key={feature.featureKey}
                  feature={feature}
                  draft={featureDraft}
                  busy={busy}
                  isSaving={featureMutations.upsert.isPending}
                  isRemoving={featureMutations.remove.isPending}
                  onUpdateDraft={(updater) => updateFeatureDraft(feature.featureKey, updater)}
                  onSave={() => handleSaveFeature(feature.featureKey)}
                  onDelete={() => handleDeleteFeature(feature.featureKey)}
                />
              );
            })}
          </div>
        ) : null}

        {unconfigured.length > 0 ? (
          <div className="space-y-2">
            <div className="text-xs font-medium tracking-wide text-text-muted">{t('modelManagement:models.featureSection.unconfigured')}</div>
            {unconfigured.map((feature) => {
              const featureDraft = featureDrafts[feature.featureKey];
              if (!featureDraft) return null;
              const busy = activeFeatureKey === feature.featureKey && (featureMutations.upsert.isPending || featureMutations.remove.isPending);
              return (
                <FeatureRow
                  key={feature.featureKey}
                  feature={feature}
                  draft={featureDraft}
                  busy={busy}
                  isSaving={featureMutations.upsert.isPending}
                  isRemoving={featureMutations.remove.isPending}
                  onUpdateDraft={(updater) => updateFeatureDraft(feature.featureKey, updater)}
                  onSave={() => handleSaveFeature(feature.featureKey)}
                  onDelete={() => handleDeleteFeature(feature.featureKey)}
                />
              );
            })}
          </div>
        ) : null}

        {!editableFeatures.length && !featureDefinitionsQuery.isLoading ? (
          <EmptyState title={t('modelManagement:models.featureSection.empty')} />
        ) : null}
      </div>
    </Card>
  );
}
