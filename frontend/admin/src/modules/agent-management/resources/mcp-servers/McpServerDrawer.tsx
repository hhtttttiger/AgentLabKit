import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/shared/ui/Button';
import { FormModal } from '@/shared/ui/FormModal';
import { SelectField, TextField, ToggleField } from '@/shared/ui/FormFields';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { JsonEditor } from '@/shared/ui/JsonEditor';
import type { CreateMcpServerRequest, McpServerDetailView, McpTransport } from './types';
import { emptyMcpServerDraft } from './types';

const am = 'agentManagement:';

const transportOptions: { value: McpTransport; label: string }[] = [
  { value: 'stdio', label: 'stdio' },
  { value: 'sse', label: 'sse' },
  { value: 'http', label: 'http' },
];

function validateDraft(draft: CreateMcpServerRequest, t: (key: string) => string) {
  const errors: Partial<Record<'name' | 'endpoint' | 'command', string>> = {};
  if (!(draft.name ?? '').trim()) errors.name = t(`${am}mcpServers.drawer.nameRequired`);
  if (draft.transport === 'stdio' && !(draft.command ?? '').trim()) errors.command = t(`${am}mcpServers.drawer.stdioCommandRequired`);
  if (draft.transport !== 'stdio' && !(draft.endpoint ?? '').trim()) errors.endpoint = t(`${am}mcpServers.drawer.httpUrlRequired`);
  return errors;
}

function tagsToString(tags: string[]): string {
  return tags.join(', ');
}

function stringToTags(value: string): string[] {
  return value.split(',').map((tag) => tag.trim()).filter(Boolean);
}

export function McpServerDrawer({
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
  initialValue: McpServerDetailView | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (model: CreateMcpServerRequest) => Promise<void>;
}) {
  const { t } = useTranslation(['common', 'agentManagement']);
  const [draft, setDraft] = useState<CreateMcpServerRequest>(emptyMcpServerDraft);
  const [tagsInput, setTagsInput] = useState('');
  const waitingForEditDetail = mode === 'edit' && open && initialValue === null && !error;

  useEffect(() => {
    if (!open) return;

    if (mode === 'create') {
      setDraft(emptyMcpServerDraft);
      setTagsInput('');
      return;
    }

    if (initialValue) {
      setDraft({
        name: initialValue.name,
        transport: initialValue.transport,
        endpoint: initialValue.endpoint,
        command: initialValue.command,
        isEnabled: initialValue.isEnabled,
        toolNamePrefix: initialValue.toolNamePrefix,
        tags: initialValue.tags,
        config: initialValue.config,
      });
      setTagsInput(tagsToString(initialValue.tags));
    }
  }, [open, mode, initialValue]);

  const validationErrors = validateDraft(draft, t);

  return (
    <FormModal
      open={open}
      title={mode === 'create' ? t(`${am}mcpServers.drawer.titleCreate`) : t(`${am}mcpServers.drawer.titleEdit`)}
      description={t(`${am}mcpServers.drawer.description`)}
      onClose={onClose}
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose}>
            {t(`${am}common.cancel`)}
          </Button>
          <Button
            onClick={() => onSubmit(draft)}
            disabled={loading || waitingForEditDetail || Object.keys(validationErrors).length > 0}
          >
            {loading
              ? t(`${am}common.submitting`)
              : mode === 'create'
                ? t(`${am}mcpServers.drawer.buttonCreate`)
                : t(`${am}mcpServers.drawer.buttonEdit`)}
          </Button>
        </div>
      }
    >
      <div className="space-y-5">
        {error && <InlineMessage tone="error">{error}</InlineMessage>}
        {waitingForEditDetail && (
          <InlineMessage tone="info">{t(`${am}mcpServers.drawer.loadingDetail`)}</InlineMessage>
        )}

        <TextField
          label={t(`${am}mcpServers.drawer.nameLabel`)}
          value={draft.name}
          error={validationErrors.name}
          placeholder={t(`${am}mcpServers.drawer.namePlaceholder`)}
          disabled={mode === 'edit'}
          onChange={(e) => setDraft((current) => ({ ...current, name: e.target.value }))}
        />

        <SelectField
          label={t(`${am}mcpServers.drawer.transportLabel`)}
          value={draft.transport}
          onChange={(e) =>
            setDraft((current) => ({
              ...current,
              transport: e.target.value as McpTransport,
              endpoint: e.target.value === 'stdio' ? null : current.endpoint,
              command: e.target.value === 'stdio' ? current.command : null,
            }))
          }
        >
          {transportOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </SelectField>

        {draft.transport === 'stdio' ? (
          <TextField
            label="Command"
            value={draft.command ?? ''}
            error={validationErrors.command}
            placeholder={t(`${am}mcpServers.drawer.commandPlaceholder`)}
            onChange={(e) => setDraft((current) => ({ ...current, command: e.target.value || null }))}
          />
        ) : (
          <TextField
            label="URL"
            value={draft.endpoint ?? ''}
            error={validationErrors.endpoint}
            placeholder={t(`${am}mcpServers.drawer.urlPlaceholder`)}
            onChange={(e) => setDraft((current) => ({ ...current, endpoint: e.target.value || null }))}
          />
        )}

        <TextField
          label={t(`${am}mcpServers.drawer.toolNamePrefix`)}
          value={draft.toolNamePrefix ?? ''}
          placeholder={t(`${am}mcpServers.drawer.toolNamePrefixPlaceholder`)}
          onChange={(e) => setDraft((current) => ({ ...current, toolNamePrefix: e.target.value || null }))}
        />

        <TextField
          label={t(`${am}mcpServers.drawer.tagsLabel`)}
          value={tagsInput}
          placeholder={t(`${am}mcpServers.drawer.tagsPlaceholder`)}
          hint={t(`${am}mcpServers.drawer.tagsHint`)}
          onChange={(e) => {
            setTagsInput(e.target.value);
            setDraft((current) => ({ ...current, tags: stringToTags(e.target.value) }));
          }}
        />

        <JsonEditor
          label={t(`${am}mcpServers.drawer.fullConfig`)}
          kind="object"
          placeholder='{ "args": ["-y", "@modelcontextprotocol/server-filesystem"] }'
          value={Object.keys(draft.config).length === 0 ? '' : JSON.stringify(draft.config)}
          onChange={(value) => {
            try {
              setDraft((current) => ({ ...current, config: (value ?? '').trim() ? JSON.parse(value) : {} }));
            } catch {
              // ignore parse errors mid-typing
            }
          }}
          hint={t(`${am}mcpServers.drawer.configHint`)}
        />

        <ToggleField
          label={t(`${am}mcpServers.drawer.enabledLabel`)}
          checked={draft.isEnabled}
          onChange={(checked) => setDraft((current) => ({ ...current, isEnabled: checked }))}
        />
      </div>
    </FormModal>
  );
}
