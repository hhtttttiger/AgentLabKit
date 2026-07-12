import { useEffect, useState, type ReactNode } from 'react';
import {
  DndContext,
  PointerSensor,
  closestCenter,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import { GripVertical, Plus, Settings2, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/shared/lib/cn';
import { Button } from '@/shared/ui/Button';
import { Card } from '@/shared/ui/Card';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { NumberField, SelectField, TextField } from '@/shared/ui/FormFields';
import type { LlmModelFeatureView } from '../../lib/contracts';
import { parseAllowedValues, toFeatureValueJson, validateFeatureValueInput } from '../../lib/features';
import {
  buildFeatureDraft,
  useFeatureEditorDrafts,
  type EditableFeature,
  type FeatureEditorDraft,
} from '../../lib/useFeatureEditorDrafts';

function DroppableContainer({
  id,
  title,
  count,
  children,
}: {
  id: 'configured' | 'unconfigured';
  title: string;
  count: number;
  children: ReactNode;
}) {
  const { setNodeRef, isOver } = useDroppable({ id });

  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <h4 className={cn('text-sm font-semibold', id === 'configured' ? 'text-primary' : 'text-text-muted')}>{title}</h4>
        <span className="text-xs text-text-muted">({count})</span>
      </div>
      <div
        ref={setNodeRef}
        className={cn(
          'min-h-[120px] space-y-2 rounded-lg border-2 p-3 transition-colors',
          id === 'configured' ? 'border-primary/20 bg-primary/5' : 'border-dashed border-border-subtle',
          isOver && 'border-primary bg-primary/10',
        )}
      >
        {children}
      </div>
    </div>
  );
}

function FeatureEditModal({
  feature,
  draft,
  open,
  isSaving,
  onClose,
  onUpdateDraft,
  onSave,
}: {
  feature: EditableFeature;
  draft: FeatureEditorDraft;
  open: boolean;
  isSaving: boolean;
  onClose: () => void;
  onUpdateDraft: (updater: (current: FeatureEditorDraft) => FeatureEditorDraft) => void;
  onSave: () => void;
}) {
  const { t } = useTranslation(['common', 'modelManagement']);
  const allowedValues = parseAllowedValues(feature.allowedValuesJson);
  const valueError = draft.isSupported
    ? validateFeatureValueInput(
        { valueType: feature.valueType, allowedValuesJson: feature.allowedValuesJson },
        draft.valueInput,
      )
    : null;

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-lg bg-surface p-6">
        <div className="mb-4 flex items-center gap-3">
          <Settings2 size={20} className="text-primary" />
          <div>
            <h3 className="text-lg font-semibold">{t('modelManagement:models.featureSection.dnd.editModal.title')}</h3>
            <p className="text-sm text-text-muted">
              {feature.displayName} ({feature.featureKey})
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium">{t('modelManagement:models.featureSection.dnd.editModal.enableLabel')}</label>
            <button
              type="button"
              onClick={() => onUpdateDraft((current) => ({ ...current, isSupported: !current.isSupported }))}
              className={cn(
                'relative h-6 w-10 shrink-0 rounded-full transition',
                draft.isSupported ? 'bg-primary' : 'bg-border-strong',
              )}
            >
              <span
                className={cn(
                  'absolute top-0.5 h-5 w-5 rounded-full bg-surface transition',
                  draft.isSupported ? 'left-[18px]' : 'left-0.5',
                )}
              />
            </button>
          </div>

          {draft.isSupported ? (
            <div>
              {feature.valueType === 'boolean' ? (
                <button
                  type="button"
                  onClick={() => onUpdateDraft((current) => ({ ...current, valueInput: current.valueInput === 'true' ? 'false' : 'true' }))}
                  className={cn(
                    'w-full rounded-lg border p-3 text-left transition',
                    draft.valueInput === 'true' ? 'border-primary bg-primary/5' : 'border-border',
                  )}
                  >
                   {draft.valueInput === 'true'
                     ? t('modelManagement:models.featureSection.dnd.editModal.booleanTrue')
                     : t('modelManagement:models.featureSection.dnd.editModal.booleanFalse')}
                 </button>
               ) : feature.valueType === 'enum' && allowedValues.length > 0 ? (
                 <SelectField
                   label={t('modelManagement:models.featureSection.dnd.editModal.featureValue')}
                  value={draft.valueInput}
                  error={valueError}
                  onChange={(event) => onUpdateDraft((current) => ({ ...current, valueInput: event.target.value }))}
                >
                  {allowedValues.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </SelectField>
              ) : feature.valueType === 'int' || feature.valueType === 'number' ? (
                <NumberField
                   label={t('modelManagement:models.featureSection.dnd.editModal.featureValue')}
                  value={draft.valueInput}
                  error={valueError}
                  step={feature.valueType === 'int' ? 1 : 'any'}
                  onChange={(event) => onUpdateDraft((current) => ({ ...current, valueInput: event.target.value }))}
                />
              ) : (
                <TextField
                   label={t('modelManagement:models.featureSection.dnd.editModal.featureValue')}
                  value={draft.valueInput}
                  error={valueError}
                  onChange={(event) => onUpdateDraft((current) => ({ ...current, valueInput: event.target.value }))}
                />
              )}
            </div>
          ) : null}

          <div className="grid gap-3 sm:grid-cols-2">
            <TextField
              label={t('modelManagement:models.featureSection.dnd.editModal.source')}
              value={draft.source}
              fieldSize="compact"
              onChange={(event) => onUpdateDraft((current) => ({ ...current, source: event.target.value }))}
            />
            <TextField
              label={t('modelManagement:models.featureSection.dnd.editModal.remark')}
              value={draft.remark}
              fieldSize="compact"
              onChange={(event) => onUpdateDraft((current) => ({ ...current, remark: event.target.value }))}
            />
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose}>
            {t('modelManagement:models.featureSection.dnd.editModal.cancel')}
          </Button>
          <Button onClick={onSave} disabled={isSaving || Boolean(valueError)}>
            {isSaving
              ? t('modelManagement:models.featureSection.dnd.editModal.saving')
              : t('modelManagement:models.featureSection.dnd.editModal.save')}
          </Button>
        </div>
      </div>
    </div>
  );
}

function DraggableFeatureItem({
  feature,
  draft,
  isConfigured,
  busy,
  onEdit,
  onToggleSupport,
  onAdd,
  onRemove,
}: {
  feature: EditableFeature;
  draft: FeatureEditorDraft;
  isConfigured: boolean;
  busy: boolean;
  onEdit: () => void;
  onToggleSupport: () => void;
  onAdd: () => void;
  onRemove: () => void;
}) {
  const { t } = useTranslation(['common', 'modelManagement']);
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: feature.featureKey,
    disabled: busy,
  });

  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
    : undefined;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'group flex items-center gap-3 rounded-lg border p-3 transition-all',
        isDragging ? 'z-50 opacity-50' : 'border-border bg-surface hover:border-border-strong hover:shadow-sm',
        !draft.isSupported && 'opacity-60',
      )}
    >
      <button
        type="button"
        aria-label={t('modelManagement:models.featureSection.dnd.dragAriaLabel', { name: feature.displayName })}
        className="touch-none cursor-grab text-text-muted hover:text-text active:cursor-grabbing"
        {...attributes}
        {...listeners}
      >
        <GripVertical size={18} />
      </button>

      <div className="min-w-0 flex-1">
        <div className={cn('text-sm font-medium', draft.isSupported ? 'text-text' : 'text-text-muted line-through')}>
          {feature.displayName}
        </div>
        {draft.hasExisting ? (
          <div className="mt-1 flex items-center gap-2 text-xs text-text-muted">
            <span>{t('modelManagement:models.featureSection.dnd.valuePrefix')}{draft.valueInput || t('modelManagement:models.featureSection.dnd.valueNotSet')}</span>
            <button type="button" onClick={onEdit} className="text-primary hover:underline">
              {t('modelManagement:models.featureSection.dnd.edit')}
            </button>
          </div>
        ) : null}
      </div>

      {isConfigured ? (
        <div className="flex items-center gap-2">
          <button
            type="button"
            aria-label={t('modelManagement:models.featureSection.dnd.removeAriaLabel', { name: feature.displayName })}
            onClick={onRemove}
            className="rounded-md px-2 py-1 text-xs font-medium text-danger transition hover:bg-danger/10"
            disabled={busy}
          >
            <span className="inline-flex items-center gap-1">
              <Trash2 size={14} />
               {t('modelManagement:models.featureSection.dnd.remove')}
             </span>
           </button>
          <button
            type="button"
            aria-label={t('modelManagement:models.featureSection.dnd.toggleAriaLabel', { name: feature.displayName })}
            onClick={onToggleSupport}
            className={cn(
              'relative h-5 w-9 shrink-0 rounded-full transition',
              draft.isSupported ? 'bg-primary' : 'bg-border-strong',
            )}
            disabled={busy}
          >
            <span
              className={cn(
                'absolute top-0.5 h-4 w-4 rounded-full bg-surface transition',
                draft.isSupported ? 'left-[14px]' : 'left-0.5',
              )}
            />
          </button>
        </div>
      ) : (
        <button
          type="button"
           aria-label={t('modelManagement:models.featureSection.dnd.addAriaLabel', { name: feature.displayName })}
          onClick={onAdd}
          className="rounded-md px-2 py-1 text-xs font-medium text-primary transition hover:bg-primary/10"
          disabled={busy}
        >
          <span className="inline-flex items-center gap-1">
            <Plus size={14} />
             {t('modelManagement:models.featureSection.dnd.add')}
           </span>
         </button>
      )}
    </div>
  );
}

export function ModelFeatureSectionDnd({
  modelKey,
  features,
}: {
  modelKey: string;
  features: LlmModelFeatureView[];
}) {
  const { t } = useTranslation(['common', 'modelManagement']);
  const {
    featureDefinitionsQuery,
    featureMutations,
    editableFeatures,
    featureDrafts,
    updateFeatureDraft,
    getFeature,
    featureActionError,
    setFeatureActionError,
    activeFeatureKey,
    setActiveFeatureKey,
  } = useFeatureEditorDrafts(modelKey, features);

  const [configuredKeys, setConfiguredKeys] = useState<string[]>([]);
  const [unconfiguredKeys, setUnconfiguredKeys] = useState<string[]>([]);
  const [editingFeatureKey, setEditingFeatureKey] = useState<string | null>(null);

  useEffect(() => {
    const currentFeatureMap = new Map(features.map((item) => [item.featureKey, item]));
    const nextConfiguredKeys: string[] = [];
    const nextUnconfiguredKeys: string[] = [];

    for (const feature of editableFeatures) {
      if (currentFeatureMap.has(feature.featureKey)) {
        nextConfiguredKeys.push(feature.featureKey);
      } else {
        nextUnconfiguredKeys.push(feature.featureKey);
      }
    }

    setConfiguredKeys(nextConfiguredKeys);
    setUnconfiguredKeys(nextUnconfiguredKeys);
  }, [editableFeatures, features]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    }),
  );

  const handleAddFeature = async (featureKey: string) => {
    const feature = getFeature(featureKey);
    const draft = featureDrafts[featureKey];
    if (!feature || !draft) {
      return;
    }

    setFeatureActionError(null);
    setActiveFeatureKey(featureKey);

    try {
      await featureMutations.upsert.mutateAsync({
        modelKey,
        featureKey,
        model: {
          featureKey,
          isSupported: true,
          valueJson: toFeatureValueJson(
            { valueType: feature.valueType, allowedValuesJson: feature.allowedValuesJson },
            draft.valueInput,
          ),
          source: 'manual',
          remark: null,
        },
      });

      setConfiguredKeys((current) => [...current, featureKey]);
      setUnconfiguredKeys((current) => current.filter((item) => item !== featureKey));
      updateFeatureDraft(featureKey, (current) => ({ ...current, hasExisting: true }));
    } catch (error) {
      setFeatureActionError(featureMutations.getMutationMessage(error));
    } finally {
      setActiveFeatureKey(null);
    }
  };

  const handleRemoveFeature = async (featureKey: string) => {
    const feature = getFeature(featureKey);
    if (!feature) {
      return;
    }

    setFeatureActionError(null);
    setActiveFeatureKey(featureKey);

    try {
      await featureMutations.remove.mutateAsync({
        modelKey,
        featureKey,
      });

      setConfiguredKeys((current) => current.filter((item) => item !== featureKey));
      setUnconfiguredKeys((current) => [...current, featureKey]);
      updateFeatureDraft(featureKey, () => buildFeatureDraft(feature));
    } catch (error) {
      setFeatureActionError(featureMutations.getMutationMessage(error));
    } finally {
      setActiveFeatureKey(null);
    }
  };

  const handleSaveFeature = async (featureKey: string) => {
    const feature = getFeature(featureKey);
    const draft = featureDrafts[featureKey];
    if (!feature || !draft) {
      return;
    }

    setFeatureActionError(null);
    setActiveFeatureKey(featureKey);

    try {
      await featureMutations.upsert.mutateAsync({
        modelKey,
        featureKey,
        model: {
          featureKey,
          isSupported: draft.isSupported,
          valueJson: draft.isSupported
            ? toFeatureValueJson(
                { valueType: feature.valueType, allowedValuesJson: feature.allowedValuesJson },
                draft.valueInput,
              )
            : null,
          source: draft.source.trim() || 'manual',
          remark: draft.remark.trim() || null,
        },
      });

      updateFeatureDraft(featureKey, (current) => ({ ...current, hasExisting: true }));
      setEditingFeatureKey(null);
    } catch (error) {
      setFeatureActionError(featureMutations.getMutationMessage(error));
    } finally {
      setActiveFeatureKey(null);
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const activeId = event.active.id as string;
    const overId = event.over?.id as string | undefined;

    if (!overId) {
      return;
    }

    if (overId === 'configured' && unconfiguredKeys.includes(activeId)) {
      void handleAddFeature(activeId);
    }

    if (overId === 'unconfigured' && configuredKeys.includes(activeId)) {
      void handleRemoveFeature(activeId);
    }
  };

  return (
    <Card
      title={t('modelManagement:models.featureSection.cardTitle')}
      description={t('modelManagement:models.featureSection.configuredCount', {
        configured: configuredKeys.length,
        total: editableFeatures.length,
      })}
    >
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <div className="grid gap-6 md:grid-cols-2">
          <DroppableContainer id="unconfigured" title={t('modelManagement:models.featureSection.dnd.unconfiguredTitle')} count={unconfiguredKeys.length}>
            {unconfiguredKeys.length === 0 ? (
              <div className="flex h-20 items-center justify-center text-sm text-text-muted">{t('modelManagement:models.featureSection.dnd.unconfiguredEmpty')}</div>
            ) : (
              unconfiguredKeys.map((featureKey) => {
                const feature = getFeature(featureKey);
                const draft = featureDrafts[featureKey];
                if (!feature || !draft) {
                  return null;
                }

                return (
                  <DraggableFeatureItem
                    key={featureKey}
                    feature={feature}
                    draft={draft}
                    isConfigured={false}
                    busy={activeFeatureKey === featureKey}
                    onEdit={() => {}}
                    onToggleSupport={() => {}}
                    onAdd={() => void handleAddFeature(featureKey)}
                    onRemove={() => {}}
                  />
                );
              })
            )}
          </DroppableContainer>

          <DroppableContainer id="configured" title={t('modelManagement:models.featureSection.dnd.configuredTitle')} count={configuredKeys.length}>
            {configuredKeys.length === 0 ? (
              <div className="flex h-20 items-center justify-center text-sm text-text-muted">{t('modelManagement:models.featureSection.dnd.configuredEmpty')}</div>
            ) : (
              configuredKeys.map((featureKey) => {
                const feature = getFeature(featureKey);
                const draft = featureDrafts[featureKey];
                if (!feature || !draft) {
                  return null;
                }

                return (
                  <div key={featureKey}>
                    <DraggableFeatureItem
                      feature={feature}
                      draft={draft}
                      isConfigured
                      busy={activeFeatureKey === featureKey}
                      onEdit={() => setEditingFeatureKey(featureKey)}
                      onToggleSupport={() => {
                        updateFeatureDraft(featureKey, (current) => ({ ...current, isSupported: !current.isSupported }));
                        void handleSaveFeature(featureKey);
                      }}
                      onAdd={() => {}}
                      onRemove={() => void handleRemoveFeature(featureKey)}
                    />
                    <FeatureEditModal
                      feature={feature}
                      draft={draft}
                      open={editingFeatureKey === featureKey}
                      isSaving={featureMutations.upsert.isPending && activeFeatureKey === featureKey}
                      onClose={() => setEditingFeatureKey(null)}
                      onUpdateDraft={(updater) => updateFeatureDraft(featureKey, updater)}
                      onSave={() => void handleSaveFeature(featureKey)}
                    />
                  </div>
                );
              })
            )}
          </DroppableContainer>
        </div>

        {featureActionError ? (
          <div className="mt-4">
            <InlineMessage tone="error">{featureActionError}</InlineMessage>
          </div>
        ) : null}

        {featureDefinitionsQuery.isLoading ? (
          <div className="mt-4 text-sm text-text-secondary">{t('modelManagement:models.featureSection.loading')}</div>
        ) : null}

        {!featureDefinitionsQuery.isLoading && editableFeatures.length === 0 ? (
          <div className="mt-4 text-center text-sm text-text-muted">{t('modelManagement:models.featureSection.empty')}</div>
        ) : null}

        <div className="mt-4 rounded-lg bg-background-subtle p-3 text-xs text-text-muted">
          {t('modelManagement:models.featureSection.dnd.hint')}
        </div>
      </DndContext>
    </Card>
  );
}
