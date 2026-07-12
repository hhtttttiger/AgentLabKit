import { useTranslation } from 'react-i18next';
import { AgentTraceView } from '@/shared/agent-trace/AgentTraceView';
import { FormModal } from '@/shared/ui/FormModal';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { useAuditDetail } from './hooks';

const am = 'agentManagement:';

export function AuditDetailDrawer({
  agentKey,
  runId,
  open,
  onClose,
}: {
  agentKey: string;
  runId: string | null;
  open: boolean;
  onClose: () => void;
}) {
  const { t } = useTranslation(['common', 'agentManagement']);
  const detailQuery = useAuditDetail(agentKey, open ? runId : null);

  return (
    <FormModal
      open={open}
      onClose={onClose}
      title={t(`${am}audits.detail.title`)}
      description={t(`${am}audits.detail.description`)}
      widthClassName="max-w-4xl"
    >
      {detailQuery.isError ? (
        <InlineMessage tone="error">{t(`${am}audits.detail.loadError`)}</InlineMessage>
      ) : null}

      <div className="min-h-[640px] overflow-hidden rounded-[2px] border border-border bg-background-subtle/40">
        <AgentTraceView
          trace={detailQuery.data ?? null}
          emptyTitle={detailQuery.isLoading ? t(`${am}audits.detail.loadingTitle`) : t(`${am}audits.detail.emptyTitle`)}
          emptyDescription={detailQuery.isLoading ? t(`${am}audits.detail.loadingDescription`) : t(`${am}audits.detail.emptyDescription`)}
        />
      </div>
    </FormModal>
  );
}
