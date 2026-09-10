import { useState } from 'react';
import { FileText, HelpCircle, RotateCw } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { FormModal } from '@/shared/ui/FormModal';
import { Button } from '@/shared/ui/Button';
import { Badge } from '@/shared/ui/Badge';
import { useToast } from '@/shared/ui/Toast';
import { formatAdminDateTime } from '@/shared/i18n/formatters';
import { useAdminLocale } from '@/shared/i18n/useAdminLocale';
import { ProcessingStatusBadge } from './ProcessingStatusBadge';
import { ProcessingPipeline } from './ProcessingPipeline';
import { SegmentViewer } from '../../segment/components/SegmentViewer';
import { useProcessingStatus, useDocumentIndexes, useDocumentMutations } from '../hooks';
import { formatFileSize, getStageLabel, isDocumentStageKey, type ProcessingStage } from '../../../lib/formatters';
import { formatRecallTime, getKnowledgeDocumentTypeLabel } from '../../../lib/ranking';
import type { KbDocumentView } from '../../../lib/contracts';

type Tab = 'overview' | 'pipeline' | 'segments';

// Keys are prefixed with the namespace: this component's translate hook
// lists ['common', 'knowledgeBase'], so unprefixed keys hit `common`.
const TABS: { key: Tab; labelKey: string }[] = [
  { key: 'overview', labelKey: 'knowledgeBase:documentDetail.tabs.overview' },
  { key: 'pipeline', labelKey: 'knowledgeBase:documentDetail.tabs.pipeline' },
  { key: 'segments', labelKey: 'knowledgeBase:documentDetail.tabs.segments' },
];

export function DocumentDetailDrawer({
  kbId,
  document,
  onClose,
}: {
  kbId: string;
  document: KbDocumentView | null;
  onClose: () => void;
}) {
  const [tab, setTab] = useState<Tab>('overview');
  const { t } = useTranslation(['common', 'knowledgeBase']);
  const { toast } = useToast();
  useAdminLocale();

  const processingQuery = useProcessingStatus(
    kbId,
    document?.id ?? '',
    document?.ingestStatus === 'Pending' || document?.ingestStatus === 'Processing',
  );

  const indexesQuery = useDocumentIndexes(kbId, document?.id ?? '');
  const mutations = useDocumentMutations(kbId);

  if (!document) return null;

  const currentStage = (processingQuery.data?.currentStage ?? document.ingestStatus) as ProcessingStage;
  const isProcessing = document.ingestStatus === 'Pending' || document.ingestStatus === 'Processing';
  const indexes = indexesQuery.data ?? [];

  return (
    <FormModal
      open={!!document}
      title={document.sourceType === 'File'
        ? (document.fileName ?? t('knowledgeBase:document.untitledFile'))
        : (document.qaQuestion ?? t('knowledgeBase:documents.qaPairFallback'))}
      description={document.sourceType === 'File' ? document.contentType : undefined}
      onClose={onClose}
      widthClassName="max-w-2xl"
    >
      {/* Tab bar */}
      <div className="mb-5 flex gap-1 border-b border-border">
        {TABS.map((tabDef) => (
          <button
            key={tabDef.key}
            type="button"
            className={`px-4 pb-2.5 text-sm font-medium transition ${
              tab === tabDef.key
                ? 'border-b-2 border-primary text-text'
                : 'text-text-muted hover:text-text'
            }`}
            onClick={() => setTab(tabDef.key)}
          >
            {t(tabDef.labelKey)}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'overview' && (
        <OverviewTab
          document={document}
          onReindex={() =>
            mutations.reindex.mutate(document.id, {
              onSuccess: () => toast(t('toast.reindexSubmitted')),
              onError: () => toast(t('toast.operationFailed'), 'error'),
            })
          }
        />
      )}
      {tab === 'pipeline' && (
        <PipelineTab
          currentStage={currentStage}
          stageProgress={processingQuery.data?.stageProgress}
          isProcessing={isProcessing}
          ingestError={document.ingestError}
          indexes={indexes}
        />
      )}
      {tab === 'segments' && (
        <SegmentViewer kbId={kbId} docId={document.id} />
      )}
    </FormModal>
  );
}

/* ── Overview ── */

function OverviewTab({
  document,
  onReindex,
}: {
  document: KbDocumentView;
  onReindex: () => void;
}) {
  const { t } = useTranslation('knowledgeBase');
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 text-sm">
        <InfoField label={t('documentDetail.fields.type')}>
          <Badge tone={document.sourceType === 'File' ? 'neutral' : 'success'}>
            {document.sourceType === 'File' ? (
              <span className="flex items-center gap-1"><FileText size={12} /> {t('document.typeFile')}</span>
            ) : (
              <span className="flex items-center gap-1"><HelpCircle size={12} /> {t(getKnowledgeDocumentTypeLabel(document.sourceType))}</span>
            )}
          </Badge>
        </InfoField>
        <InfoField label={t('documentDetail.fields.status')}>
          <ProcessingStatusBadge status={document.ingestStatus} />
        </InfoField>
        {document.sourceType === 'File' && (
          <InfoField label={t('documentDetail.fields.fileSize')}>{formatFileSize(document.fileSize)}</InfoField>
        )}
        <InfoField label={t('documentDetail.fields.createdAt')}>{formatAdminDateTime(document.createdAtUtc)}</InfoField>
        <InfoField label={t('documentDetail.fields.recallTotal')}>{t('document.recallCountTotal', { count: document.recallCount ?? 0 })}</InfoField>
        <InfoField label={t('documentDetail.fields.lastRecall')}>{formatRecallTime(document.lastRecalledAtUtc) ?? t('document.neverRecalled')}</InfoField>
        {document.ingestError && (
          <div className="col-span-2">
            <InfoField label={t('documentDetail.fields.error')}>
              <span className="text-error">{document.ingestError}</span>
            </InfoField>
          </div>
        )}
      </div>

      {/* QA content */}
      {document.sourceType === 'QaPair' && (
        <div className="space-y-2 rounded-[2px] border border-border p-4">
          <div>
            <span className="text-xs font-semibold text-text-muted">{t('documentDetail.question')}</span>
            <p className="mt-1 text-sm text-text">{document.qaQuestion}</p>
          </div>
          <div>
            <span className="text-xs font-semibold text-text-muted">{t('documentDetail.answer')}</span>
            <p className="mt-1 text-sm text-text">{document.qaAnswer}</p>
          </div>
        </div>
      )}

      <div className="flex gap-2">
        <Button variant="secondary" onClick={onReindex}>
          <RotateCw size={14} />
          {t('documents.reindex')}
        </Button>
      </div>
    </div>
  );
}

/* ── Pipeline ── */

function PipelineTab({
  currentStage,
  stageProgress,
  isProcessing,
  ingestError,
  indexes,
}: {
  currentStage: ProcessingStage;
  stageProgress?: import('../../../lib/contracts').StageProgressItem[];
  isProcessing: boolean;
  ingestError?: string;
  indexes: import('../../../lib/contracts').DocumentIndexView[];
}) {
  const { t } = useTranslation('knowledgeBase');
  // Unknown index statuses arrive as raw lowercase backend values.
  const translateStageLabel = (label: string) => {
    if (isDocumentStageKey(label)) return t(label);
    return label.charAt(0).toUpperCase() + label.slice(1);
  };
  return (
    <div className="space-y-5">
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <h4 className="text-sm font-semibold uppercase tracking-wide text-text-muted">{t('documentDetail.pipeline.statusTitle')}</h4>
          {isProcessing && (
            <span className="text-xs text-text-muted">{t('documentDetail.pipeline.autoRefresh')}</span>
          )}
        </div>
        <div className="rounded-[2px] border border-border p-4">
          <ProcessingPipeline currentStage={currentStage} stageProgress={stageProgress} />
        </div>
        {ingestError && (
          <p className="rounded-lg border border-error/20 bg-error-subtle p-3 text-xs text-error">
            {ingestError}
          </p>
        )}
      </div>

      {indexes.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-semibold uppercase tracking-wide text-text-muted">{t('documentDetail.pipeline.indexTitle')}</h4>
          <div className="space-y-2">
            {indexes.map((idx) => (
              <div key={idx.id} className="flex items-center justify-between rounded-lg border border-border px-4 py-2 text-sm">
                <span className="text-text">{idx.indexType}</span>
                <Badge tone={idx.status === 'Completed' ? 'success' : idx.status === 'Failed' ? 'danger' : 'warning'}>
                  {translateStageLabel(getStageLabel(idx.status))}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Shared ── */

function InfoField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <span className="block text-xs text-text-muted">{label}</span>
      <div className="mt-0.5 text-text">{children}</div>
    </div>
  );
}
