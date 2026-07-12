import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, Trash2 } from 'lucide-react';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { FormModal } from '@/shared/ui/FormModal';
import { EmptyState } from '@/shared/ui/EmptyState';
import { SelectField, TextField, ToggleField } from '@/shared/ui/FormFields';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import type { KnowledgeBaseBindingWriteModel } from '../../lib/contracts';
import type { KnowledgeBaseBindingCandidate } from '../knowledge-base-bindings/types';

const am = 'agentManagement';

type Row = KnowledgeBaseBindingWriteModel & {
  knowledgeBaseName: string;
  knowledgeBaseStatus: string | null;
  createdAtUtc: string;
  updatedAtUtc: string | null;
};

const statusTone: Record<string, 'success' | 'warning' | 'neutral'> = {
  Active: 'success',
  Processing: 'warning',
  Disabled: 'neutral',
  Deleted: 'neutral',
};

export function VersionKnowledgeBaseBindingSection({
  readOnly,
  hasUsableKnowledgeSearch,
  rows,
  candidates,
  validationErrors,
  onAdd,
  onUpdate,
  onRemove,
}: {
  readOnly: boolean;
  hasUsableKnowledgeSearch: boolean;
  rows: Row[];
  candidates: KnowledgeBaseBindingCandidate[];
  validationErrors: Record<string, string>;
  onAdd: (binding: KnowledgeBaseBindingWriteModel) => void;
  onUpdate: (index: number, binding: KnowledgeBaseBindingWriteModel) => void;
  onRemove: (index: number) => void;
}) {
  const { t } = useTranslation(['common', 'agentManagement']);
  const [createOpen, setCreateOpen] = useState(false);
  const [draft, setDraft] = useState<KnowledgeBaseBindingWriteModel>({
    id: null,
    knowledgeBaseId: '',
    sortOrder: rows.length * 10,
    isEnabled: true,
    config: {},
  });

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-text">{t(`${am}.versions.kbBindings.sectionTitle`)}</h4>
        {!readOnly && (
          <Button
            variant="secondary"
            disabled={candidates.length === 0}
            onClick={() => setCreateOpen(true)}
          >
            <Plus size={14} />
            {t(`${am}.versions.kbBindings.addButton`)}
          </Button>
        )}
      </div>

      {readOnly && (
        <InlineMessage tone="info">
          {t(`${am}.versions.kbBindings.readonlyInfo`)}
        </InlineMessage>
      )}

      {!readOnly && rows.length > 0 && !hasUsableKnowledgeSearch && (
        <InlineMessage tone="info">
          {t(`${am}.versions.kbBindings.missingToolWarning`)}
        </InlineMessage>
      )}

      {rows.length === 0 ? (
        <EmptyState
          title={t(`${am}.versions.kbBindings.emptyTitle`)}
          description={t(`${am}.versions.kbBindings.emptyDescription`)}
        />
      ) : (
        <div className="space-y-3">
          {rows.map((row, index) => (
            <div key={row.id ?? `${row.knowledgeBaseId}-${index}`} className="rounded-[2px] border border-border bg-background-subtle p-4">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <div className="font-medium text-text">{row.knowledgeBaseName}</div>
                  <div className="mt-1 flex items-center gap-2">
                    {row.knowledgeBaseStatus && (
                      <Badge tone={statusTone[row.knowledgeBaseStatus] ?? 'neutral'}>
                        {row.knowledgeBaseStatus}
                      </Badge>
                    )}
                    <span className="font-mono text-xs text-text-muted">{row.knowledgeBaseId}</span>
                  </div>
                </div>
                {!readOnly && (
                  <Button variant="ghost" onClick={() => onRemove(index)}>
                    <Trash2 size={14} />
                  </Button>
                )}
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <TextField
                  label={t(`${am}.versions.kbBindings.sortLabel`)}
                  type="number"
                  value={String(row.sortOrder)}
                  disabled={readOnly}
                  onChange={(event) => onUpdate(index, { ...row, sortOrder: Number(event.target.value) })}
                />
                <ToggleField
                  label={t(`${am}.versions.kbBindings.enabledLabel`)}
                  checked={row.isEnabled}
                  disabled={readOnly}
                  onChange={(checked) => onUpdate(index, { ...row, isEnabled: checked })}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      <FormModal
        open={createOpen}
        title={t(`${am}.versions.kbBindings.drawerTitle`)}
        description={t(`${am}.versions.kbBindings.drawerDescription`)}
        onClose={() => setCreateOpen(false)}
        footer={(
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setCreateOpen(false)}>
              {t(`${am}.common.cancel`)}
            </Button>
            <Button
              disabled={!draft.knowledgeBaseId}
              onClick={() => {
                onAdd(draft);
                setCreateOpen(false);
                setDraft({
                  id: null,
                  knowledgeBaseId: '',
                  sortOrder: rows.length * 10,
                  isEnabled: true,
                  config: {},
                });
              }}
            >
              {t(`${am}.versions.kbBindings.saveButton`)}
            </Button>
          </div>
        )}
      >
        <div className="space-y-4">
          <SelectField
            label={t(`${am}.versions.kbBindings.selectLabel`)}
            error={validationErrors.kb_create_knowledgeBaseId}
            value={draft.knowledgeBaseId}
            onChange={(event) => setDraft((current) => ({ ...current, knowledgeBaseId: event.target.value }))}
          >
            <option value="">{t(`${am}.versions.kbBindings.selectPlaceholder`)}</option>
            {candidates.map((candidate) => (
              <option key={candidate.value} value={candidate.value}>
                {candidate.label}
              </option>
            ))}
          </SelectField>
          <TextField
            label={t(`${am}.versions.kbBindings.sortLabel`)}
            type="number"
            value={String(draft.sortOrder)}
            onChange={(event) => setDraft((current) => ({ ...current, sortOrder: Number(event.target.value) }))}
          />
          <ToggleField
            label={t(`${am}.versions.kbBindings.enabledLabel`)}
            checked={draft.isEnabled}
            onChange={(checked) => setDraft((current) => ({ ...current, isEnabled: checked }))}
          />
        </div>
      </FormModal>
    </section>
  );
}
