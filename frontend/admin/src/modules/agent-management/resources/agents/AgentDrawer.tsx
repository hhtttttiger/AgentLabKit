import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/shared/ui/Button';
import { FormModal } from '@/shared/ui/FormModal';
import { TextAreaField, TextField } from '@/shared/ui/FormFields';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { JsonEditor } from '@/shared/ui/JsonEditor';
import type { AgentDetailView, CreateAgentRequest } from '../../lib/contracts';
import { emptyAgentDraft } from './types';

const am = 'agentManagement';

function validateDraft(draft: CreateAgentRequest, t: (key: string) => string) {
  const errors: Partial<Record<keyof CreateAgentRequest, string>> = {};
  if (!(draft.agentKey ?? '').trim()) errors.agentKey = t(`${am}.agents.drawer.agentKeyRequired`);
  if (!(draft.displayName ?? '').trim()) errors.displayName = t(`${am}.agents.drawer.displayNameRequired`);
  return errors;
}

export function AgentDrawer({
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
  initialValue: AgentDetailView | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (model: CreateAgentRequest) => Promise<void>;
}) {
  const { t } = useTranslation(['common', 'agentManagement']);
  const [draft, setDraft] = useState<CreateAgentRequest>(emptyAgentDraft);
  const [advancedOpen, setAdvancedOpen] = useState(false);

  useEffect(() => {
    if (initialValue) {
      setDraft({
        agentKey: initialValue.agentKey,
        displayName: initialValue.displayName,
        description: initialValue.description ?? null,
        tags: initialValue.tags ?? [],
        metadata: initialValue.metadata ?? {},
      });
      return;
    }

    setDraft(emptyAgentDraft);
  }, [initialValue, open]);

  const validationErrors = validateDraft(draft, t);
  const isEdit = mode === 'edit';

  return (
    <FormModal
      open={open}
      title={isEdit ? t(`${am}.agents.drawer.titleEdit`) : t(`${am}.agents.drawer.titleCreate`)}
      description={
        isEdit
          ? t(`${am}.agents.drawer.descEdit`)
          : t(`${am}.agents.drawer.descCreate`)
      }
      onClose={onClose}
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose}>
            {t(`${am}.common.cancel`)}
          </Button>
          <Button
            onClick={() => onSubmit(draft)}
            disabled={loading || Object.keys(validationErrors).length > 0}
          >
            {loading
              ? t(`${am}.common.submitting`)
              : isEdit
                ? t(`${am}.agents.drawer.buttonEdit`)
                : t(`${am}.agents.drawer.buttonCreate`)}
          </Button>
        </div>
      }
    >
      <div className="space-y-5">
        {error && <InlineMessage tone="error">{error}</InlineMessage>}

        <div className="grid gap-4 md:grid-cols-2">
          <TextField
            label={t(`${am}.agents.drawer.agentKey`)}
            value={draft.agentKey}
            error={validationErrors.agentKey}
            placeholder={t(`${am}.agents.drawer.agentKeyPlaceholder`)}
            disabled={isEdit}
            onChange={(e) => setDraft((c) => ({ ...c, agentKey: e.target.value }))}
          />
          <TextField
            label={t(`${am}.agents.drawer.displayName`)}
            value={draft.displayName}
            error={validationErrors.displayName}
            onChange={(e) => setDraft((c) => ({ ...c, displayName: e.target.value }))}
          />
        </div>

        <TextAreaField
          label={t(`${am}.agents.drawer.description`)}
          value={draft.description ?? ''}
          placeholder={t(`${am}.agents.drawer.descriptionPlaceholder`)}
          rows={3}
          onChange={(e) => setDraft((c) => ({ ...c, description: e.target.value || null }))}
        />

        <div className="rounded-[2px] border border-border bg-surface">
          <button
            type="button"
            className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-text"
            onClick={() => setAdvancedOpen((c) => !c)}
          >
            <span>{t(`${am}.agents.drawer.advanced`)}</span>
            <span className="text-text-muted">
              {advancedOpen ? t(`${am}.common.collapse`) : t(`${am}.common.expand`)}
            </span>
          </button>
          {advancedOpen && (
            <div className="space-y-4 border-t border-border p-4">
              <JsonEditor
                label={t(`${am}.agents.drawer.tags`)}
                kind="array"
                value={JSON.stringify(draft.tags)}
                onChange={(v) => setDraft((c) => ({ ...c, tags: JSON.parse(v) }))}
                hint={t(`${am}.agents.drawer.tagsHint`)}
              />
              <JsonEditor
                label={t(`${am}.agents.drawer.metadata`)}
                kind="object"
                value={JSON.stringify(draft.metadata)}
                onChange={(v) => setDraft((c) => ({ ...c, metadata: JSON.parse(v) }))}
                hint={t(`${am}.agents.drawer.metadataHint`)}
              />
            </div>
          )}
        </div>
      </div>
    </FormModal>
  );
}
