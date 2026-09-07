import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { FormModal } from '@/shared/ui/FormModal';
import { Button } from '@/shared/ui/Button';
import { SelectField } from '@/shared/ui/FormFields';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { useToast } from '@/shared/ui/Toast';
import { useAgentList } from '@/modules/agent-management/resources/agents/hooks';
import { getVersionDetail, listVersions, createVersion, updateVersion } from '@/modules/agent-management/resources/versions/api';
import { ensureKnowledgeUsable, ensureVersionDefaultPolicy, versionDetailToDraft } from '@/modules/agent-management/resources/versions/draft';

export function UseKnowledgeInAgentModal({
  open,
  knowledgeBaseId,
  knowledgeBaseName,
  onClose,
}: {
  open: boolean;
  knowledgeBaseId: string;
  knowledgeBaseName: string;
  onClose: () => void;
}) {
  const { t } = useTranslation(['common', 'knowledgeBase']);
  const navigate = useNavigate();
  const { toast } = useToast();
  const agentsQuery = useAgentList({ page: 1, pageSize: 100 });
  const [agentKey, setAgentKey] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const reset = () => {
    setAgentKey('');
    setError(null);
    onClose();
  };

  const useKnowledge = async () => {
    if (!agentKey) return;
    setSaving(true);
    setError(null);
    try {
      const agent = agentsQuery.data?.items.find((item) => item.agentKey === agentKey);
      if (!agent) throw new Error(t('knowledgeBase:detail.useInAgentNoTarget'));

      const versions = await listVersions(agent.agentKey, { page: 1, pageSize: 100 });
      const draftRow = versions.items.find((version) => version.versionStatus === 'draft');
      const publishedRow = versions.items.find(
        (version) => version.versionStatus === 'published' && version.versionNumber === agent.publishedVersionNumber,
      );
      const sourceRow = draftRow ?? publishedRow;
      if (!sourceRow) throw new Error(t('knowledgeBase:detail.useInAgentNoVersion'));

      const source = await getVersionDetail(agent.agentKey, sourceRow.versionNumber);
      const draft = versionDetailToDraft(source);
      const composed = ensureKnowledgeUsable({
        toolBindings: draft.toolBindings,
        knowledgeBaseBindings: draft.knowledgeBaseBindings,
        knowledgeBaseId,
      });
      const payload = ensureVersionDefaultPolicy({ ...draft, ...composed });

      let targetVersionNumber: number;
      if (draftRow) {
        await updateVersion(agent.agentKey, draftRow.versionNumber, { ...payload, rowVersion: source.rowVersion });
        targetVersionNumber = draftRow.versionNumber;
      } else {
        const created = await createVersion(agent.agentKey, payload);
        targetVersionNumber = created.versionNumber;
      }

      toast(t('knowledgeBase:detail.useInAgentSuccess', { name: knowledgeBaseName, versionNumber: targetVersionNumber }));
      reset();
      navigate(`/agents/${encodeURIComponent(agent.agentKey)}?tab=build&version=${targetVersionNumber}&knowledge=${encodeURIComponent(knowledgeBaseId)}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t('knowledgeBase:detail.useInAgentFailed'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <FormModal
      open={open}
      title={t('knowledgeBase:detail.useInAgentTitle')}
      description={t('knowledgeBase:detail.useInAgentDescription', { name: knowledgeBaseName })}
      onClose={reset}
      footer={(
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={reset}>{t('common:actions.cancel')}</Button>
          <Button disabled={!agentKey || saving || agentsQuery.isLoading} onClick={useKnowledge}>
            {saving ? t('knowledgeBase:detail.useInAgentSaving') : t('knowledgeBase:detail.useInAgentButton')}
          </Button>
        </div>
      )}
    >
      {error && <InlineMessage tone="error">{error}</InlineMessage>}
      <SelectField
        label={t('knowledgeBase:detail.useInAgentSelectLabel')}
        value={agentKey}
        disabled={agentsQuery.isLoading || saving}
        onChange={(event) => setAgentKey(event.target.value)}
      >
        <option value="">{t('knowledgeBase:detail.useInAgentSelectPlaceholder')}</option>
        {(agentsQuery.data?.items ?? []).map((agent) => (
          <option key={agent.agentKey} value={agent.agentKey}>
            {agent.displayName} ({agent.agentKey}) · {agent.status}
          </option>
        ))}
      </SelectField>
    </FormModal>
  );
}
