import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, Trash2 } from 'lucide-react';
import { Button } from '@/shared/ui/Button';
import { FormModal } from '@/shared/ui/FormModal';
import { SelectField, TextAreaField, TextField, ToggleField } from '@/shared/ui/FormFields';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { JsonEditor } from '@/shared/ui/JsonEditor';
import type { InvocationMode, ToolBindingWriteModel } from '../../lib/contracts';
import type { CreateSkillRequest, PromptSection, SkillDetailView, SkillSummaryView } from './types';
import { emptySkillDraft } from './types';
import { useSkill } from './hooks';

const am = 'agentManagement:';

const SKILL_KEY_PATTERN = /^[a-z][a-z0-9_.-]*$/;

const emptyToolBinding: ToolBindingWriteModel = {
  toolName: '',
  displayName: null,
  description: null,
  invocationMode: 'auto',
  isRequired: false,
  config: {},
  sortOrder: 0,
  isEnabled: true,
};

function validateDraft(draft: CreateSkillRequest, mode: 'create' | 'edit', t: (key: string, opts?: Record<string, unknown>) => string) {
  const errors: Record<string, string> = {};
  if (mode === 'create') {
    if (!(draft.skillKey ?? '').trim()) {
      errors.skillKey = t(`${am}skills.drawer.skillKeyRequired`);
    } else if (!SKILL_KEY_PATTERN.test(draft.skillKey)) {
      errors.skillKey = t(`${am}skills.drawer.skillKeyPattern`);
    }
  }
  if (!(draft.displayName ?? '').trim()) errors.displayName = t(`${am}skills.drawer.displayNameRequired`);
  if (!(draft.version ?? '').trim()) errors.version = t(`${am}skills.drawer.versionRequired`);
  (draft.promptSections ?? []).forEach((section, index) => {
    if (!(section.key ?? '').trim()) errors[`section_${index}_key`] = t(`${am}skills.drawer.promptSectionKeyRequired`, { number: index + 1 });
    if (!(section.content ?? '').trim()) errors[`section_${index}_content`] = t(`${am}skills.drawer.promptSectionContentRequired`, { number: index + 1 });
  });
  (draft.toolBindings ?? []).forEach((binding, index) => {
    if (!(binding.toolName ?? '').trim()) errors[`tool_${index}_toolName`] = t(`${am}skills.drawer.toolNameRequired`, { number: index + 1 });
  });
  return errors;
}

function detailToDraft(detail: SkillDetailView): CreateSkillRequest {
  return {
    skillKey: detail.skillKey,
    displayName: detail.displayName,
    description: detail.description,
    version: detail.version,
    tags: detail.tags,
    promptSections: detail.promptSections,
    toolBindings: detail.toolBindings,
    configSchema: detail.configSchema,
    spec: detail.spec,
    orchestration: detail.orchestration,
  };
}

function PromptSectionRow({
  index,
  section,
  onChange,
  onRemove,
  errors,
}: {
  index: number;
  section: PromptSection;
  onChange: (updated: PromptSection) => void;
  onRemove: () => void;
  errors: Record<string, string>;
}) {
  const { t } = useTranslation(['common', 'agentManagement']);
  return (
    <div className="rounded-[2px] border border-border bg-background-subtle p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-sm font-medium text-text">
          {t(`${am}skills.drawer.promptSectionTitle`, { number: index + 1 })}
        </span>
        <Button variant="ghost" onClick={onRemove}>
          <Trash2 size={14} />
        </Button>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <TextField
          label="Key"
          value={section.key}
          error={errors[`section_${index}_key`]}
          placeholder={t(`${am}skills.drawer.sectionKeyPlaceholder`)}
          onChange={(e) => onChange({ ...section, key: e.target.value })}
        />
        <TextField
          label={t(`${am}skills.drawer.sectionSortOrder`)}
          type="number"
          value={String(section.sortOrder)}
          onChange={(e) => onChange({ ...section, sortOrder: Number(e.target.value) })}
        />
      </div>
      <div className="mt-3">
        <TextAreaField
          label={t(`${am}skills.drawer.sectionContent`)}
          value={section.content}
          error={errors[`section_${index}_content`]}
          rows={4}
          onChange={(e) => onChange({ ...section, content: e.target.value })}
        />
      </div>
    </div>
  );
}

function ToolBindingRow({
  index,
  binding,
  onChange,
  onRemove,
  errors,
}: {
  index: number;
  binding: ToolBindingWriteModel;
  onChange: (updated: ToolBindingWriteModel) => void;
  onRemove: () => void;
  errors: Record<string, string>;
}) {
  const { t } = useTranslation(['common', 'agentManagement']);

  const invocationModeOptions: { value: InvocationMode; label: string }[] = [
    { value: 'auto', label: t(`${am}skills.drawer.invocationModeAuto`) },
    { value: 'manual_only', label: t(`${am}skills.drawer.invocationModeManual`) },
    { value: 'disabled', label: t(`${am}skills.drawer.invocationModeDisabled`) },
  ];

  return (
    <div className="rounded-[2px] border border-border bg-background-subtle p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-sm font-medium text-text">
          {t(`${am}skills.drawer.toolTitle`, { number: index + 1 })}
        </span>
        <Button variant="ghost" onClick={onRemove}>
          <Trash2 size={14} />
        </Button>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <TextField
          label={t(`${am}skills.drawer.toolNameLabel`)}
          value={binding.toolName}
          error={errors[`tool_${index}_toolName`]}
          onChange={(e) => onChange({ ...binding, toolName: e.target.value })}
        />
        <TextField
          label={t(`${am}skills.drawer.displayNameLabel`)}
          value={binding.displayName ?? ''}
          onChange={(e) => onChange({ ...binding, displayName: e.target.value || null })}
        />
        <TextField
          label={t(`${am}skills.drawer.descriptionLabel`)}
          value={binding.description ?? ''}
          onChange={(e) => onChange({ ...binding, description: e.target.value || null })}
        />
        <SelectField
          label={t(`${am}skills.drawer.invocationModeLabel`)}
          value={binding.invocationMode}
          onChange={(e) => onChange({ ...binding, invocationMode: e.target.value as InvocationMode })}
        >
          {invocationModeOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </SelectField>
      </div>
      <div className="mt-3 flex gap-4">
        <ToggleField label={t(`${am}skills.drawer.requiredLabel`)} checked={binding.isRequired} onChange={(checked) => onChange({ ...binding, isRequired: checked })} />
        <ToggleField label={t(`${am}skills.drawer.enabledLabel`)} checked={binding.isEnabled} onChange={(checked) => onChange({ ...binding, isEnabled: checked })} />
      </div>
    </div>
  );
}

export function SkillDrawer({
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
  initialValue: SkillSummaryView | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (model: CreateSkillRequest) => Promise<void>;
}) {
  const { t } = useTranslation(['common', 'agentManagement']);
  const [draft, setDraft] = useState<CreateSkillRequest>(emptySkillDraft);
  const [configOpen, setConfigOpen] = useState(false);
  const skillKeyForDetail = mode === 'edit' && initialValue ? initialValue.skillKey : '';
  const detailQuery = useSkill(skillKeyForDetail);

  useEffect(() => {
    if (!open) return;
    setConfigOpen(false);
    if (mode === 'edit' && detailQuery.data) setDraft(detailToDraft(detailQuery.data));
    if (mode === 'create') setDraft(emptySkillDraft);
  }, [open, mode, detailQuery.data]);

  const validationErrors = validateDraft(draft, mode, t);

  const updateSection = (index: number, updated: PromptSection) => {
    setDraft((current) => ({
      ...current,
      promptSections: current.promptSections.map((section, itemIndex) => (itemIndex === index ? updated : section)),
    }));
  };

  const updateTool = (index: number, updated: ToolBindingWriteModel) => {
    setDraft((current) => ({
      ...current,
      toolBindings: current.toolBindings.map((binding, itemIndex) => (itemIndex === index ? updated : binding)),
    }));
  };

  return (
    <FormModal
      open={open}
      title={mode === 'create' ? t(`${am}skills.drawer.titleCreate`) : t(`${am}skills.drawer.titleEdit`)}
      description={t(`${am}skills.drawer.description`)}
      onClose={onClose}
      widthClassName="max-w-3xl"
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose}>{t(`${am}common.cancel`)}</Button>
          <Button onClick={() => onSubmit(draft)} disabled={loading || Object.keys(validationErrors).length > 0}>
            {loading
              ? t(`${am}common.submitting`)
              : mode === 'create'
                ? t(`${am}skills.drawer.buttonCreate`)
                : t(`${am}skills.drawer.buttonEdit`)}
          </Button>
        </div>
      }
    >
      <div className="space-y-5">
        {error && <InlineMessage tone="error">{error}</InlineMessage>}
        {mode === 'edit' && detailQuery.isLoading && (
          <InlineMessage tone="info">{t(`${am}skills.drawer.loadingDetail`)}</InlineMessage>
        )}

        <div className="grid gap-4 md:grid-cols-2">
          <TextField
            label={t(`${am}skills.drawer.skillKeyLabel`)}
            value={draft.skillKey}
            error={validationErrors.skillKey}
            placeholder={t(`${am}skills.drawer.skillKeyPlaceholder`)}
            disabled={mode === 'edit'}
            onChange={(e) => setDraft((current) => ({ ...current, skillKey: e.target.value }))}
          />
          <TextField
            label={t(`${am}skills.drawer.displayNameLabel`)}
            value={draft.displayName}
            error={validationErrors.displayName}
            onChange={(e) => setDraft((current) => ({ ...current, displayName: e.target.value }))}
          />
          <TextField
            label={t(`${am}skills.drawer.versionLabel`)}
            value={draft.version}
            error={validationErrors.version}
            placeholder={t(`${am}skills.drawer.versionPlaceholder`)}
            onChange={(e) => setDraft((current) => ({ ...current, version: e.target.value }))}
          />
          <div className="md:col-span-2">
            <TextAreaField
              label={t(`${am}skills.drawer.descriptionLabel`)}
              value={draft.description}
              rows={3}
              onChange={(e) => setDraft((current) => ({ ...current, description: e.target.value }))}
            />
          </div>
          <div className="md:col-span-2">
            <TextField
              label={t(`${am}skills.drawer.tagsLabel`)}
              value={draft.tags.join(', ')}
              placeholder={t(`${am}skills.drawer.tagsPlaceholder`)}
              onChange={(e) =>
                setDraft((current) => ({
                  ...current,
                  tags: e.target.value.split(',').map((tag) => tag.trim()).filter(Boolean),
                }))
              }
            />
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-text">{t(`${am}skills.drawer.promptSectionsTitle`)}</h4>
            <Button
              variant="secondary"
              onClick={() => setDraft((current) => ({
                ...current,
                promptSections: [...current.promptSections, { key: '', content: '', sortOrder: current.promptSections.length }],
              }))}
            >
              <Plus size={14} />
              {t(`${am}skills.drawer.addPromptSection`)}
            </Button>
          </div>
          {draft.promptSections.length === 0 && (
            <p className="text-sm text-text-muted">{t(`${am}skills.drawer.emptyPromptSections`)}</p>
          )}
          {draft.promptSections.map((section, index) => (
            <PromptSectionRow
              key={index}
              index={index}
              section={section}
              errors={validationErrors}
              onChange={(updated) => updateSection(index, updated)}
              onRemove={() => setDraft((current) => ({ ...current, promptSections: current.promptSections.filter((_, itemIndex) => itemIndex !== index) }))}
            />
          ))}
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-text">{t(`${am}skills.drawer.toolBindingsTitle`)}</h4>
            <Button
              variant="secondary"
              onClick={() => setDraft((current) => ({
                ...current,
                toolBindings: [...current.toolBindings, { ...emptyToolBinding, sortOrder: current.toolBindings.length }],
              }))}
            >
              <Plus size={14} />
              {t(`${am}skills.drawer.addTool`)}
            </Button>
          </div>
          {draft.toolBindings.length === 0 && (
            <p className="text-sm text-text-muted">{t(`${am}skills.drawer.emptyToolBindings`)}</p>
          )}
          {draft.toolBindings.map((binding, index) => (
            <ToolBindingRow
              key={index}
              index={index}
              binding={binding}
              errors={validationErrors}
              onChange={(updated) => updateTool(index, updated)}
              onRemove={() => setDraft((current) => ({ ...current, toolBindings: current.toolBindings.filter((_, itemIndex) => itemIndex !== index) }))}
            />
          ))}
        </div>

        <div className="rounded-[2px] border border-border bg-surface">
          <button
            type="button"
            className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-text"
            onClick={() => setConfigOpen((current) => !current)}
          >
            <span>{t(`${am}skills.drawer.advancedConfig`)}</span>
            <span className="text-text-muted">
              {configOpen ? t(`${am}common.collapse`) : t(`${am}common.expand`)}
            </span>
          </button>
          {configOpen && (
            <div className="border-t border-border p-4">
              <JsonEditor
                label={t(`${am}skills.drawer.configSchemaLabel`)}
                kind="object"
                placeholder='{ "type": "object" }'
                value={Object.keys(draft.configSchema).length === 0 ? '' : JSON.stringify(draft.configSchema)}
                onChange={(value) => {
                  try {
                    setDraft((current) => ({ ...current, configSchema: (value ?? '').trim() ? JSON.parse(value) : {} }));
                  } catch {
                    // ignore parse errors mid-typing
                  }
                }}
              />
            </div>
          )}
        </div>
      </div>
    </FormModal>
  );
}
