import { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Plus, Trash2 } from 'lucide-react';
import { listKnowledgeBases } from '@/modules/knowledge-base/resources/knowledge-base/api';
import { kbQueryKeys } from '@/modules/knowledge-base/resources/knowledge-base/queryKeys';
import { getErrorMessage } from '@/shared/api/errors';
import { Button } from '@/shared/ui/Button';
import { FormModal } from '@/shared/ui/FormModal';
import { SelectField, TextAreaField, TextField, ToggleField } from '@/shared/ui/FormFields';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { JsonEditor } from '@/shared/ui/JsonEditor';
import { useToast } from '@/shared/ui/Toast';
import { useModelList } from '@/modules/model-management/resources/model-cards/hooks';
import { useMcpServerList } from '../mcp-servers/hooks';
import { useSkillList } from '../skills/hooks';
import { useToolDefinitionList } from '../tools/hooks';
import type {
  InvocationMode,
  McpBindingWriteModel,
  SkillBindingWriteModel,
  ToolBindingWriteModel,
  VersionDetailView,
} from '../../lib/contracts';
import { emptyToolBinding, emptyVersionDraft } from './types';
import type { VersionEditorDraft } from './draft';
import {
  createEmptyMcpBinding,
  createEmptySkillBinding,
  displayToPolicy,
  emptyToolOverride,
  ensureVersionDefaultPolicy,
  policyToDisplay,
  validateVersionDraft,
  versionDetailToDraft,
} from './draft';
import { useVersionMutations } from './hooks';
import { VersionKnowledgeBaseBindingSection } from './VersionKnowledgeBaseBindingSection';
import { agentManagementQueryKeys } from '../../lib/queryKeys';
import {
  buildKnowledgeBaseBindingCandidates,
  hasUsableKnowledgeSearchBinding,
  mergeKnowledgeBaseBindingRows,
} from '../knowledge-base-bindings/types';

const am = 'modules.agentManagement';

function ToolBindingRow({
  index,
  binding,
  onChange,
  onRemove,
  toolNameError,
  title,
  availableTools,
  disabled = false,
}: {
  index: number;
  binding: ToolBindingWriteModel;
  onChange: (updated: ToolBindingWriteModel) => void;
  onRemove: () => void;
  toolNameError?: string;
  title?: string;
  availableTools?: Array<{ toolName: string; displayName: string; sourceType: string }>;
  disabled?: boolean;
}) {
  const { t } = useTranslation('common');
  const hasOptions = availableTools && availableTools.length > 0;

  const invocationModeOptions: { value: InvocationMode; label: string }[] = [
    { value: 'auto', label: t(`${am}.versions.drawer.invocationModeAuto`) },
    { value: 'manual_only', label: t(`${am}.versions.drawer.invocationModeManual`) },
    { value: 'disabled', label: t(`${am}.versions.drawer.invocationModeDisabled`) },
  ];

  return (
    <div className="rounded-[2px] border border-border bg-background-subtle p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-sm font-medium text-text">{title ?? t(`${am}.versions.drawer.toolLabel`, { number: index + 1 })}</span>
        <Button variant="ghost" disabled={disabled} onClick={onRemove}>
          <Trash2 size={14} />
        </Button>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {hasOptions ? (
          <SelectField
            label={t(`${am}.versions.drawer.toolNameLabel`)}
            value={binding.toolName}
            disabled={disabled}
            onChange={(e) => onChange({ ...binding, toolName: e.target.value })}
          >
            <option value="">{t(`${am}.versions.drawer.selectTool`)}</option>
            {availableTools.map((tool) => (
              <option key={tool.toolName} value={tool.toolName}>
                {tool.displayName} ({tool.toolName})
              </option>
            ))}
          </SelectField>
        ) : (
          <TextField
            label={t(`${am}.versions.drawer.toolNameLabel`)}
            value={binding.toolName}
            error={toolNameError}
            disabled={disabled}
            onChange={(e) => onChange({ ...binding, toolName: e.target.value })}
          />
        )}
        <TextField
          label={t(`${am}.versions.drawer.toolDisplayNameLabel`)}
          value={binding.displayName ?? ''}
          disabled={disabled}
          onChange={(e) => onChange({ ...binding, displayName: e.target.value || null })}
        />
        <TextField
          label={t(`${am}.versions.drawer.toolDescriptionLabel`)}
          value={binding.description ?? ''}
          disabled={disabled}
          onChange={(e) => onChange({ ...binding, description: e.target.value || null })}
        />
        <SelectField
          label={t(`${am}.versions.drawer.toolInvocationModeLabel`)}
          value={binding.invocationMode}
          disabled={disabled}
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
        <ToggleField
          label={t(`${am}.versions.drawer.toolRequiredLabel`)}
          checked={binding.isRequired}
          disabled={disabled}
          onChange={(checked) => onChange({ ...binding, isRequired: checked })}
        />
        <ToggleField
          label={t(`${am}.versions.drawer.toolEnabledLabel`)}
          checked={binding.isEnabled}
          disabled={disabled}
          onChange={(checked) => onChange({ ...binding, isEnabled: checked })}
        />
      </div>
    </div>
  );
}

function McpBindingRow({
  index,
  binding,
  serverOptions,
  onChange,
  onRemove,
  errors,
  disabled = false,
}: {
  index: number;
  binding: McpBindingWriteModel;
  serverOptions: { value: string; label: string }[];
  onChange: (updated: McpBindingWriteModel) => void;
  onRemove: () => void;
  errors: Record<string, string>;
  disabled?: boolean;
}) {
  const { t } = useTranslation('common');
  return (
    <div className="rounded-[2px] border border-border bg-background-subtle p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-sm font-medium text-text">{t(`${am}.versions.drawer.mcpLabel`, { number: index + 1 })}</span>
        <Button variant="ghost" disabled={disabled} onClick={onRemove}>
          <Trash2 size={14} />
        </Button>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <SelectField
          label="MCP Server"
          value={binding.serverName}
          error={errors[`mcp_${index}_serverName`]}
          disabled={disabled}
          onChange={(e) => onChange({ ...binding, serverName: e.target.value })}
        >
          <option value="">{t(`${am}.versions.drawer.selectMcpServer`)}</option>
          {serverOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </SelectField>
        <TextField
          label={t(`${am}.versions.drawer.toolWhitelist`)}
          value={binding.toolWhitelist?.join(', ') ?? ''}
          placeholder={t(`${am}.versions.drawer.toolWhitelistPlaceholder`)}
          disabled={disabled}
          onChange={(e) => {
            const raw = e.target.value.trim();
            onChange({
              ...binding,
              toolWhitelist: raw ? raw.split(',').map((item) => item.trim()).filter(Boolean) : null,
            });
          }}
        />
      </div>
      <div className="mt-3">
        <ToggleField
          label={t(`${am}.versions.drawer.mcpEnabledLabel`)}
          checked={binding.isEnabled}
          disabled={disabled}
          onChange={(checked) => onChange({ ...binding, isEnabled: checked })}
        />
      </div>
    </div>
  );
}

function SkillBindingRow({
  index,
  binding,
  skillOptions,
  onChange,
  onRemove,
  errors,
  disabled = false,
}: {
  index: number;
  binding: SkillBindingWriteModel;
  skillOptions: { value: string; label: string }[];
  onChange: (updated: SkillBindingWriteModel) => void;
  onRemove: () => void;
  errors: Record<string, string>;
  disabled?: boolean;
}) {
  const { t } = useTranslation('common');

  const updateToolOverride = (toolIndex: number, updated: ToolBindingWriteModel) => {
    onChange({
      ...binding,
      toolOverrides: binding.toolOverrides.map((tool, currentIndex) =>
        currentIndex === toolIndex ? updated : tool,
      ),
    });
  };

  return (
    <div className="rounded-[2px] border border-border bg-background-subtle p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-sm font-medium text-text">{t(`${am}.versions.drawer.skillLabel`, { number: index + 1 })}</span>
        <Button variant="ghost" disabled={disabled} onClick={onRemove}>
          <Trash2 size={14} />
        </Button>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <SelectField
          label={t(`${am}.versions.drawer.skillKeyLabel`)}
          value={binding.skillKey}
          error={errors[`skill_${index}_skillKey`]}
          disabled={disabled}
          onChange={(e) => onChange({ ...binding, skillKey: e.target.value })}
        >
          <option value="">{t(`${am}.versions.drawer.selectSkill`)}</option>
          {skillOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </SelectField>
        <TextField
          label={t(`${am}.versions.drawer.skillSortLabel`)}
          type="number"
          value={String(binding.sortOrder)}
          disabled={disabled}
          onChange={(e) => onChange({ ...binding, sortOrder: Number(e.target.value) })}
        />
      </div>
      <div className="mt-3">
        <JsonEditor
          label={t(`${am}.versions.drawer.configOverrides`)}
          kind="object"
          placeholder="{}"
          value={Object.keys(binding.configOverrides).length === 0 ? '' : JSON.stringify(binding.configOverrides)}
          disabled={disabled}
          onChange={(value) => {
            try {
              onChange({ ...binding, configOverrides: (value ?? '').trim() ? JSON.parse(value) : {} });
            } catch {
              // ignore parse errors while typing
            }
          }}
        />
      </div>
      <div className="mt-4 space-y-3">
        <div className="flex items-center justify-between">
          <h5 className="text-sm font-semibold text-text">{t(`${am}.versions.drawer.toolOverrides`)}</h5>
          <Button
            variant="secondary"
            disabled={disabled}
            onClick={() =>
              onChange({
                ...binding,
                toolOverrides: [...binding.toolOverrides, emptyToolOverride(binding.toolOverrides.length)],
              })
            }
          >
            <Plus size={14} />
            {t(`${am}.versions.drawer.addToolOverride`)}
          </Button>
        </div>
        {binding.toolOverrides.length === 0 && <p className="text-sm text-text-muted">{t(`${am}.versions.drawer.emptyToolOverrides`)}</p>}
        {binding.toolOverrides.map((toolOverride, toolIndex) => (
          <ToolBindingRow
            key={toolIndex}
            index={toolIndex}
            binding={toolOverride}
            title={t(`${am}.versions.drawer.toolOverrideLabel`, { number: toolIndex + 1 })}
            disabled={disabled}
            toolNameError={errors[`skill_${index}_tool_${toolIndex}_toolName`]}
            onChange={(updated) => updateToolOverride(toolIndex, updated)}
            onRemove={() =>
              onChange({
                ...binding,
                toolOverrides: binding.toolOverrides.filter((_, currentIndex) => currentIndex !== toolIndex),
              })
            }
          />
        ))}
      </div>
      <div className="mt-3">
        <ToggleField
          label={t(`${am}.versions.drawer.skillEnabledLabel`)}
          checked={binding.isEnabled}
          disabled={disabled}
          onChange={(checked) => onChange({ ...binding, isEnabled: checked })}
        />
      </div>
    </div>
  );
}

export function VersionDrawer({
  open,
  agentKey,
  editVersion,
  seedVersion,
  readOnly = false,
  onClose,
}: {
  open: boolean;
  agentKey: string;
  editVersion?: VersionDetailView | null;
  seedVersion?: VersionDetailView | null;
  readOnly?: boolean;
  onClose: () => void;
}) {
  const { t } = useTranslation('common');
  const { toast } = useToast();
  const isEdit = !!editVersion && !readOnly;
  const bindingSourceVersion = editVersion ?? seedVersion ?? null;
  const sourceVersionNumber = bindingSourceVersion?.versionNumber ?? null;
  const [draft, setDraft] = useState<VersionEditorDraft>(emptyVersionDraft);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const queryClient = useQueryClient();
  const mutations = useVersionMutations(agentKey);
  const knowledgeBasesQuery = useQuery({
    queryKey: kbQueryKeys.list({ status: 'active', pageSize: 100 }),
    queryFn: () => listKnowledgeBases({ page: 1, pageSize: 100 }),
  });
  const modelsQuery = useModelList({ isEnabled: true, page: 1, pageSize: 100 });
  const mcpServersQuery = useMcpServerList({});
  const skillsQuery = useSkillList({ publishedOnly: true });
  const toolDefinitionsQuery = useToolDefinitionList({ status: 'active' });
  const activeMutation = isEdit ? mutations.update : mutations.create;
  const validationErrors = validateVersionDraft(draft);
  const editorSessionKey = open
    ? `${readOnly ? 'read' : isEdit ? 'edit' : 'create'}:${sourceVersionNumber ?? 'new'}`
    : null;
  const modelOptions = modelsQuery.data?.items ?? [];

  const mcpServerOptions = useMemo(
    () => (mcpServersQuery.data ?? []).map((server) => ({ value: server.name, label: server.name })),
    [mcpServersQuery.data],
  );
  const skillOptions = useMemo(
    () => (skillsQuery.data ?? []).map((skill) => ({ value: skill.skillKey, label: skill.displayName })),
    [skillsQuery.data],
  );
  const availableToolOptions = useMemo(
    () => (toolDefinitionsQuery.data ?? []).map((tool) => ({
      toolName: tool.toolName,
      displayName: tool.displayName,
      sourceType: tool.sourceType,
    })),
    [toolDefinitionsQuery.data],
  );
  const knowledgeBaseRows = useMemo(() => {
    const catalogRows = mergeKnowledgeBaseBindingRows(
      draft.knowledgeBaseBindings.map((binding, index) => ({
        id: binding.id ?? `draft-${index}`,
        knowledgeBaseId: binding.knowledgeBaseId,
        sortOrder: binding.sortOrder,
        isEnabled: binding.isEnabled,
        config: binding.config,
        createdAtUtc: '',
        updatedAtUtc: null,
      })),
      knowledgeBasesQuery.data?.items ?? [],
    );

    return catalogRows.map((row, index) => ({
      ...row,
      id: draft.knowledgeBaseBindings[index]?.id ?? null,
    }));
  }, [draft.knowledgeBaseBindings, knowledgeBasesQuery.data?.items]);
  const knowledgeBaseCandidates = useMemo(
    () => buildKnowledgeBaseBindingCandidates(
      knowledgeBasesQuery.data?.items ?? [],
      draft.knowledgeBaseBindings.map((binding, index) => ({
        id: binding.id ?? `draft-${index}`,
        knowledgeBaseId: binding.knowledgeBaseId,
        sortOrder: binding.sortOrder,
        isEnabled: binding.isEnabled,
        config: binding.config,
        createdAtUtc: '',
        updatedAtUtc: null,
      })),
    ),
    [draft.knowledgeBaseBindings, knowledgeBasesQuery.data?.items],
  );
  const hasUsableKnowledgeSearch = useMemo(
    () => hasUsableKnowledgeSearchBinding(draft.toolBindings),
    [draft.toolBindings],
  );

  const previousSessionKeyRef = useRef<string | null>(null);

  useEffect(() => {
    if (!open) {
      previousSessionKeyRef.current = null;
      return;
    }

    const sessionKey = editorSessionKey;
    if (previousSessionKeyRef.current === sessionKey) {
      return;
    }
    previousSessionKeyRef.current = sessionKey;

    setAdvancedOpen(false);
    setSubmitError(null);
    mutations.create.reset();
    mutations.update.reset();

    if (!bindingSourceVersion) {
      setDraft(emptyVersionDraft);
      return;
    }

    setDraft(versionDetailToDraft(bindingSourceVersion));
  }, [
    open,
    editorSessionKey,
    bindingSourceVersion,
    mutations.create,
    mutations.update,
  ]);

  const updateDraft = (recipe: (current: VersionEditorDraft) => VersionEditorDraft) => {
    setDraft((current) => recipe(current));
  };

  const handleSubmit = async () => {
    if (readOnly) return;

    setSubmitError(null);

    try {
      const payload = ensureVersionDefaultPolicy(draft);
      if (isEdit && editVersion) {
        await mutations.update.mutateAsync({
          versionNumber: editVersion.versionNumber,
          model: { ...payload, rowVersion: editVersion.rowVersion },
        });
      } else {
        await mutations.create.mutateAsync(payload);
      }

      await queryClient.invalidateQueries({
        queryKey: agentManagementQueryKeys.versionsRoot(agentKey),
      });

      toast(t(isEdit ? 'toast.updated' : 'toast.created'));
      onClose();
    } catch (error) {
      setSubmitError(getErrorMessage(error));
    }
  };

  const title = readOnly && editVersion
    ? t(`${am}.versions.drawer.titleView`, { versionNumber: editVersion.versionNumber })
    : editVersion
      ? t(`${am}.versions.drawer.titleEdit`, { versionNumber: editVersion.versionNumber })
      : seedVersion
        ? t(`${am}.versions.drawer.titleClone`, { versionNumber: seedVersion.versionNumber })
        : t(`${am}.versions.drawer.titleCreate`);

  const description = readOnly
    ? t(`${am}.versions.drawer.descReadonly`)
    : t(`${am}.versions.drawer.descEdit`);

  return (
    <FormModal
      open={open}
      title={title}
      description={description}
      onClose={onClose}
      widthClassName="max-w-3xl"
      footer={
        readOnly ? (
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={onClose}>
              {t(`${am}.versions.drawer.buttonClose`)}
            </Button>
          </div>
        ) : (
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={onClose}>
              {t(`${am}.versions.drawer.buttonCancel`)}
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={
                activeMutation.isPending ||
                Object.keys(validationErrors).length > 0
              }
            >
              {activeMutation.isPending
                ? t(`${am}.versions.drawer.buttonSubmitting`)
                : isEdit
                  ? t(`${am}.versions.drawer.buttonSave`)
                  : seedVersion
                    ? t(`${am}.versions.drawer.buttonCreateDraft`)
                    : t(`${am}.versions.drawer.buttonCreate`)}
            </Button>
          </div>
        )
      }
    >
      <div className="space-y-5">
        {activeMutation.error && !readOnly && (
          <InlineMessage tone="error">{mutations.getMutationMessage(activeMutation.error)}</InlineMessage>
        )}
        {submitError && <InlineMessage tone="error">{submitError}</InlineMessage>}

        <div className="grid gap-4 md:grid-cols-2">
          <SelectField
            label={t(`${am}.versions.drawer.modelLabel`)}
            value={draft.modelKey}
            disabled={readOnly}
            onChange={(e) => updateDraft((current) => ({ ...current, modelKey: e.target.value }))}
          >
            <option value="">{modelsQuery.isLoading ? t(`${am}.versions.drawer.modelLoading`) : t(`${am}.versions.drawer.modelPlaceholder`)}</option>
            {modelOptions.map((model) => (
              <option key={model.modelKey} value={model.modelKey}>
                {model.displayName} ({model.modelKey}) - {model.type}
              </option>
            ))}
          </SelectField>
          <TextField
            label={t(`${am}.versions.drawer.versionLabel`)}
            value={draft.versionLabel ?? ''}
            placeholder={t(`${am}.versions.drawer.versionPlaceholder`)}
            disabled={readOnly}
            onChange={(e) => updateDraft((current) => ({ ...current, versionLabel: e.target.value || null }))}
          />
          <TextField
            label={t(`${am}.versions.drawer.localeLabel`)}
            value={draft.defaultLocale ?? ''}
            placeholder={t(`${am}.versions.drawer.localePlaceholder`)}
            disabled={readOnly}
            onChange={(e) => updateDraft((current) => ({ ...current, defaultLocale: e.target.value || null }))}
          />
          <TextField
            label={t(`${am}.versions.drawer.changelogLabel`)}
            value={draft.changeSummary ?? ''}
            disabled={readOnly}
            onChange={(e) => updateDraft((current) => ({ ...current, changeSummary: e.target.value || null }))}
          />
        </div>

        <TextAreaField
          label="System Prompt"
          error={validationErrors.systemPromptTemplate}
          value={draft.systemPromptTemplate}
          rows={10}
          disabled={readOnly}
          onChange={(e) => updateDraft((current) => ({ ...current, systemPromptTemplate: e.target.value }))}
        />

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-text">{t(`${am}.versions.drawer.toolBindings`)}</h4>
            <Button
              variant="secondary"
              disabled={readOnly}
              onClick={() =>
                updateDraft((current) => ({
                  ...current,
                  toolBindings: [...current.toolBindings, { ...emptyToolBinding, sortOrder: current.toolBindings.length }],
                }))
              }
            >
              <Plus size={14} />
              {t(`${am}.versions.drawer.addTool`)}
            </Button>
          </div>
          {draft.toolBindings.length === 0 && <p className="text-sm text-text-muted">{t(`${am}.versions.drawer.emptyToolBindings`)}</p>}
          {draft.toolBindings.map((binding, index) => (
            <ToolBindingRow
              key={index}
              index={index}
              binding={binding}
              disabled={readOnly}
              toolNameError={validationErrors[`tool_${index}_toolName`]}
              availableTools={availableToolOptions.length > 0 ? availableToolOptions : undefined}
              onChange={(updated) =>
                updateDraft((current) => ({
                  ...current,
                  toolBindings: current.toolBindings.map((item, itemIndex) => itemIndex === index ? updated : item),
                }))
              }
              onRemove={() =>
                updateDraft((current) => ({
                  ...current,
                  toolBindings: current.toolBindings.filter((_, itemIndex) => itemIndex !== index),
                }))
              }
            />
          ))}
        </div>

        <VersionKnowledgeBaseBindingSection
          readOnly={readOnly}
          hasUsableKnowledgeSearch={hasUsableKnowledgeSearch}
          rows={knowledgeBaseRows}
          candidates={knowledgeBaseCandidates}
          validationErrors={validationErrors}
          onAdd={(binding) =>
            updateDraft((current) => ({
              ...current,
              knowledgeBaseBindings: [...current.knowledgeBaseBindings, binding],
            }))
          }
          onUpdate={(index, binding) =>
            updateDraft((current) => ({
              ...current,
              knowledgeBaseBindings: current.knowledgeBaseBindings.map((item, itemIndex) =>
                itemIndex === index ? binding : item),
            }))
          }
          onRemove={(index) =>
            updateDraft((current) => ({
              ...current,
              knowledgeBaseBindings: current.knowledgeBaseBindings.filter((_, itemIndex) => itemIndex !== index),
            }))
          }
        />

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-text">{t(`${am}.versions.drawer.mcpBindings`)}</h4>
            <Button
              variant="secondary"
              disabled={readOnly}
              onClick={() =>
                updateDraft((current) => ({
                  ...current,
                  mcpBindings: [...current.mcpBindings, createEmptyMcpBinding()],
                }))
              }
            >
              <Plus size={14} />
              {t(`${am}.versions.drawer.addMcpBinding`)}
            </Button>
          </div>
          {draft.mcpBindings.length === 0 && <p className="text-sm text-text-muted">{t(`${am}.versions.drawer.emptyMcpBindings`)}</p>}
          {draft.mcpBindings.map((binding, index) => (
            <McpBindingRow
              key={index}
              index={index}
              binding={binding}
              disabled={readOnly}
              serverOptions={mcpServerOptions}
              errors={validationErrors}
              onChange={(updated) =>
                updateDraft((current) => ({
                  ...current,
                  mcpBindings: current.mcpBindings.map((item, itemIndex) => itemIndex === index ? updated : item),
                }))
              }
              onRemove={() =>
                updateDraft((current) => ({
                  ...current,
                  mcpBindings: current.mcpBindings.filter((_, itemIndex) => itemIndex !== index),
                }))
              }
            />
          ))}
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-text">{t(`${am}.versions.drawer.skillBindings`)}</h4>
            <Button
              variant="secondary"
              disabled={readOnly}
              onClick={() =>
                updateDraft((current) => ({
                  ...current,
                  skillBindings: [...current.skillBindings, createEmptySkillBinding(current.skillBindings.length)],
                }))
              }
            >
              <Plus size={14} />
              {t(`${am}.versions.drawer.addSkillBinding`)}
            </Button>
          </div>
          {draft.skillBindings.length === 0 && <p className="text-sm text-text-muted">{t(`${am}.versions.drawer.emptySkillBindings`)}</p>}
          {draft.skillBindings.map((binding, index) => (
            <SkillBindingRow
              key={index}
              index={index}
              binding={binding}
              disabled={readOnly}
              skillOptions={skillOptions}
              errors={validationErrors}
              onChange={(updated) =>
                updateDraft((current) => ({
                  ...current,
                  skillBindings: current.skillBindings.map((item, itemIndex) => itemIndex === index ? updated : item),
                }))
              }
              onRemove={() =>
                updateDraft((current) => ({
                  ...current,
                  skillBindings: current.skillBindings.filter((_, itemIndex) => itemIndex !== index),
                }))
              }
            />
          ))}
        </div>

        <div className="rounded-[2px] border border-border bg-surface">
          <button
            type="button"
            className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-text"
            onClick={() => setAdvancedOpen((current) => !current)}
          >
            <span>{t(`${am}.versions.drawer.advancedPolicy`)}</span>
            <span className="text-text-muted">{advancedOpen ? t(`${am}.common.collapse`) : t(`${am}.common.expand`)}</span>
          </button>
          {advancedOpen && (
            <div className="space-y-4 border-t border-border p-4">
              <p className="text-xs text-text-muted">{t(`${am}.versions.drawer.advancedPolicyHint`)}</p>
              <JsonEditor
                label="Runtime Options"
                kind="object"
                placeholder='{ "maxTurns": 10 }'
                value={policyToDisplay(draft.runtimeOptions)}
                disabled={readOnly}
                onChange={(value) => updateDraft((current) => ({ ...current, runtimeOptions: displayToPolicy(value) }))}
              />
              <JsonEditor
                label="Handoff Policy"
                kind="object"
                placeholder="{}"
                value={policyToDisplay(draft.handoffPolicy)}
                disabled={readOnly}
                onChange={(value) => updateDraft((current) => ({ ...current, handoffPolicy: displayToPolicy(value) }))}
              />
              <JsonEditor
                label="Response Policy"
                kind="object"
                placeholder='{ "mode": "default" }'
                value={policyToDisplay(draft.responsePolicy)}
                disabled={readOnly}
                onChange={(value) => updateDraft((current) => ({ ...current, responsePolicy: displayToPolicy(value) }))}
              />
              <JsonEditor
                label={t(`${am}.versions.drawer.agentLocalGuardrailsPolicyLabel`)}
                kind="object"
                placeholder="{}"
                value={policyToDisplay(draft.guardrailsPolicy)}
                disabled={readOnly}
                onChange={(value) => updateDraft((current) => ({ ...current, guardrailsPolicy: displayToPolicy(value) }))}
              />
            </div>
          )}
        </div>
      </div>
    </FormModal>
  );
}
