import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { FormModal } from '@/shared/ui/FormModal';
import { SelectField, TextAreaField, TextField } from '@/shared/ui/FormFields';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { JsonEditor } from '@/shared/ui/JsonEditor';
import type { CreateToolDefinitionRequest, ToolSummaryView } from './types';
import { emptyToolDraft } from './types';

const am = 'modules.agentManagement';
const TOOL_NAME_PATTERN = /^[a-z][a-z0-9_]*$/;
const HTTP_METHODS = ['POST', 'GET', 'PUT', 'PATCH'];

function BuiltinReadOnlyView({ tool }: { tool: ToolSummaryView }) {
  const { t } = useTranslation('common');
  return (
    <div className="space-y-6">
      <InlineMessage tone="info">
        {t(`${am}.tools.drawer.builtinNotice`)}
      </InlineMessage>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <p className="text-xs text-text-muted">{t(`${am}.tools.drawer.toolNameLabel`)}</p>
          <p className="mt-1 font-mono text-sm text-text">{tool.toolName}</p>
        </div>
        <div>
          <p className="text-xs text-text-muted">{t(`${am}.tools.drawer.displayNameLabel`)}</p>
          <p className="mt-1 text-sm text-text">{tool.displayName}</p>
        </div>
        <div className="md:col-span-2">
          <p className="text-xs text-text-muted">{t(`${am}.tools.drawer.descriptionLabel`)}</p>
          <p className="mt-1 text-sm text-text">{tool.description}</p>
        </div>
        <div>
          <p className="text-xs text-text-muted">{t(`${am}.tools.drawer.timeoutLabel`)}</p>
          <p className="mt-1 text-sm text-text">{tool.timeoutSeconds}s</p>
        </div>
        <div>
          <p className="text-xs text-text-muted">{t(`${am}.tools.drawer.maxRetriesLabel`)}</p>
          <p className="mt-1 text-sm text-text">{tool.maxRetries}</p>
        </div>
        {tool.tags.length > 0 && (
          <div className="md:col-span-2">
            <p className="mb-2 text-xs text-text-muted">{t(`${am}.tools.columns.tags`)}</p>
            <div className="flex flex-wrap gap-2">
              {tool.tags.map((tag) => (
                <Badge key={tag} tone="neutral">{tag}</Badge>
              ))}
            </div>
          </div>
        )}
      </div>
      <div>
        <p className="mb-2 text-xs text-text-muted">{t(`${am}.tools.drawer.parametersSchemaLabel`)}</p>
        <JsonEditor
          label=""
          kind="object"
          value={JSON.stringify(tool.parametersSchema, null, 2)}
          onChange={() => undefined}
        />
      </div>
    </div>
  );
}

function HttpExternalForm({
  draft,
  errors,
  mode,
  onChangeDraft,
}: {
  draft: CreateToolDefinitionRequest;
  errors: Record<string, string>;
  mode: 'create' | 'edit';
  onChangeDraft: (updated: CreateToolDefinitionRequest) => void;
}) {
  const { t } = useTranslation('common');
  const set = <K extends keyof CreateToolDefinitionRequest>(
    key: K,
    value: CreateToolDefinitionRequest[K],
  ) => onChangeDraft({ ...draft, [key]: value });

  return (
    <div className="space-y-5">
      {mode === 'create' && (
        <TextField
          label={t(`${am}.tools.drawer.toolNameSnakeCase`)}
          value={draft.toolName}
          error={errors.toolName}
          placeholder="crm_lookup"
          onChange={(e) => set('toolName', e.target.value)}
        />
      )}
      <div className="grid gap-4 md:grid-cols-2">
        <TextField
          label={t(`${am}.tools.drawer.displayNameLabel`)}
          value={draft.displayName}
          error={errors.displayName}
          onChange={(e) => set('displayName', e.target.value)}
        />
        <div>
          <p className="mb-1 text-xs text-text-muted">{t(`${am}.tools.drawer.timeoutLabel`)}</p>
          <input
            type="number"
            min={1}
            value={draft.timeoutSeconds}
            className="w-full rounded-[2px] border border-border bg-surface px-3 py-2 text-sm text-text"
            onChange={(e) => set('timeoutSeconds', Number(e.target.value))}
          />
        </div>
      </div>

      <TextAreaField
        label={t(`${am}.tools.drawer.descriptionLlm`)}
        value={draft.description}
        error={errors.description}
        rows={3}
        onChange={(e) => set('description', e.target.value)}
      />

      <TextField
        label={t(`${am}.tools.drawer.endpointLabel`)}
        value={draft.endpointUrl}
        error={errors.endpointUrl}
        placeholder="https://my-service.internal/execute"
        onChange={(e) => set('endpointUrl', e.target.value)}
      />

      <div className="grid gap-4 md:grid-cols-2">
        <SelectField
          label="HTTP Method"
          value={draft.httpMethod}
          onChange={(e) => set('httpMethod', e.target.value)}
        >
          {HTTP_METHODS.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </SelectField>
        <TextField
          label="Credential Key"
          value={draft.credentialKey ?? ''}
          placeholder="CRM_API_KEY"
          onChange={(e) => set('credentialKey', e.target.value || null)}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <p className="mb-1 text-xs text-text-muted">{t(`${am}.tools.drawer.maxRetriesLabel`)}</p>
          <input
            type="number"
            min={0}
            value={draft.maxRetries}
            className="w-full rounded-[2px] border border-border bg-surface px-3 py-2 text-sm text-text"
            onChange={(e) => set('maxRetries', Number(e.target.value))}
          />
        </div>
      </div>

      <div>
        <p className="mb-1 text-xs text-text-muted">{t(`${am}.tools.drawer.tagsLabel`)}</p>
        <input
          type="text"
          value={draft.tags.join(', ')}
          placeholder="crm, read_only"
          className="w-full rounded-[2px] border border-border bg-surface px-3 py-2 text-sm text-text"
          onChange={(e) =>
            set('tags', e.target.value.split(',').map((tag) => tag.trim()).filter(Boolean))
          }
        />
      </div>

      <div>
        <JsonEditor
          label={t(`${am}.tools.drawer.parametersSchemaLabel`)}
          kind="object"
          value={JSON.stringify(draft.parametersSchema, null, 2)}
          onChange={(value) => {
            try {
              set('parametersSchema', JSON.parse(value));
            } catch {
              // ignore parse errors mid-typing
            }
          }}
        />
      </div>
    </div>
  );
}

type ToolDrawerProps = {
  open: boolean;
  onClose: () => void;
  editingTool: ToolSummaryView | null;
  onCreateSubmit: (draft: CreateToolDefinitionRequest) => Promise<void>;
  onUpdateSubmit: (toolName: string, draft: CreateToolDefinitionRequest) => Promise<void>;
  errorMessage?: string;
  loading?: boolean;
};

function validateDraft(
  draft: CreateToolDefinitionRequest,
  mode: 'create' | 'edit',
  t: (key: string) => string,
) {
  const errors: Record<string, string> = {};

  if (mode === 'create') {
    if (!(draft.toolName ?? '').trim()) {
      errors.toolName = t(`${am}.tools.drawer.toolNameRequired`);
    } else if (!TOOL_NAME_PATTERN.test(draft.toolName)) {
      errors.toolName = t(`${am}.tools.drawer.toolNamePattern`);
    }
  }

  if (!(draft.displayName ?? '').trim()) errors.displayName = t(`${am}.tools.drawer.displayNameRequired`);
  if (!(draft.description ?? '').trim()) errors.description = t(`${am}.tools.drawer.descriptionRequired`);
  if (!(draft.endpointUrl ?? '').trim()) errors.endpointUrl = t(`${am}.tools.drawer.endpointRequired`);

  return errors;
}

function draftFromExisting(tool: ToolSummaryView): CreateToolDefinitionRequest {
  return {
    toolName: tool.toolName,
    displayName: tool.displayName,
    description: tool.description,
    endpointUrl: tool.endpointUrl ?? '',
    parametersSchema: tool.parametersSchema,
    tags: tool.tags,
    httpMethod: tool.httpMethod,
    credentialKey: tool.credentialKey,
    timeoutSeconds: tool.timeoutSeconds,
    maxRetries: tool.maxRetries,
  };
}

export function ToolDrawer({
  open,
  onClose,
  editingTool,
  onCreateSubmit,
  onUpdateSubmit,
  errorMessage,
  loading,
}: ToolDrawerProps) {
  const { t } = useTranslation('common');
  const isBuiltin = editingTool?.sourceType === 'builtin';
  const mode = editingTool ? 'edit' : 'create';

  const [draft, setDraft] = useState<CreateToolDefinitionRequest>(emptyToolDraft);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (editingTool) {
      setDraft(draftFromExisting(editingTool));
    } else {
      setDraft(emptyToolDraft);
    }
    setErrors({});
  }, [editingTool, open]);

  const handleSubmit = async () => {
    const fieldErrors = validateDraft(draft, mode, t);
    if (Object.keys(fieldErrors).length > 0) {
      setErrors(fieldErrors);
      return;
    }
    setErrors({});

    if (editingTool) {
      await onUpdateSubmit(editingTool.toolName, draft);
    } else {
      await onCreateSubmit(draft);
    }
  };

  const title = editingTool
    ? isBuiltin
      ? t(`${am}.tools.drawer.titleBuiltin`, { name: editingTool.displayName })
      : t(`${am}.tools.drawer.titleEdit`, { name: editingTool.displayName })
    : t(`${am}.tools.drawer.titleCreate`);

  return (
    <FormModal
      open={open}
      onClose={onClose}
      title={title}
      footer={
        !isBuiltin && (
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={onClose} disabled={loading}>
              {t(`${am}.common.cancel`)}
            </Button>
            <Button onClick={handleSubmit} disabled={loading}>
              {loading ? t(`${am}.tools.drawer.savingButton`) : t(`${am}.tools.drawer.saveButton`)}
            </Button>
          </div>
        )
      }
    >
      <div className="space-y-6 p-6">
        {errorMessage && <InlineMessage tone="error">{errorMessage}</InlineMessage>}

        {isBuiltin ? (
          <BuiltinReadOnlyView tool={editingTool!} />
        ) : (
          <HttpExternalForm
            draft={draft}
            errors={errors}
            mode={mode}
            onChangeDraft={setDraft}
          />
        )}
      </div>
    </FormModal>
  );
}
