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
import { formatFileSize, getStageLabel, type ProcessingStage } from '../../../lib/formatters';
import { formatRecallCount, formatRecallTime, getKnowledgeDocumentTypeLabel } from '../../../lib/ranking';
import type { KbDocumentView } from '../../../lib/contracts';

type Tab = 'overview' | 'pipeline' | 'segments';

const TABS: { key: Tab; label: string }[] = [
  { key: 'overview', label: '概览' },
  { key: 'pipeline', label: '处理流水线' },
  { key: 'segments', label: '分段' },
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
  const { t } = useTranslation('common');
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
      title={document.sourceType === 'File' ? (document.fileName ?? '文件') : 'QA 对'}
      description={document.sourceType === 'File' ? document.contentType : undefined}
      onClose={onClose}
      widthClassName="max-w-2xl"
    >
      {/* Tab bar */}
      <div className="mb-5 flex gap-1 border-b border-border">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            className={`px-4 pb-2.5 text-sm font-medium transition ${
              tab === t.key
                ? 'border-b-2 border-primary text-text'
                : 'text-text-muted hover:text-text'
            }`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
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
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 text-sm">
        <InfoField label="类型">
          <Badge tone={document.sourceType === 'File' ? 'neutral' : 'success'}>
            {document.sourceType === 'File' ? (
              <span className="flex items-center gap-1"><FileText size={12} /> 文件</span>
            ) : (
              <span className="flex items-center gap-1"><HelpCircle size={12} /> {getKnowledgeDocumentTypeLabel(document.sourceType)}</span>
            )}
          </Badge>
        </InfoField>
        <InfoField label="状态">
          <ProcessingStatusBadge status={document.ingestStatus} />
        </InfoField>
        {document.sourceType === 'File' && (
          <InfoField label="文件大小">{formatFileSize(document.fileSize)}</InfoField>
        )}
        <InfoField label="创建时间">{formatAdminDateTime(document.createdAtUtc)}</InfoField>
        <InfoField label="累计被召回次数">{formatRecallCount(document)}</InfoField>
        <InfoField label="最近召回时间">{formatRecallTime(document.lastRecalledAtUtc)}</InfoField>
        {document.ingestError && (
          <div className="col-span-2">
            <InfoField label="错误信息">
              <span className="text-error">{document.ingestError}</span>
            </InfoField>
          </div>
        )}
      </div>

      {/* QA content */}
      {document.sourceType === 'QaPair' && (
        <div className="space-y-2 rounded-[2px] border border-border p-4">
          <div>
            <span className="text-xs font-semibold text-text-muted">问题</span>
            <p className="mt-1 text-sm text-text">{document.qaQuestion}</p>
          </div>
          <div>
            <span className="text-xs font-semibold text-text-muted">回答</span>
            <p className="mt-1 text-sm text-text">{document.qaAnswer}</p>
          </div>
        </div>
      )}

      <div className="flex gap-2">
        <Button variant="secondary" onClick={onReindex}>
          <RotateCw size={14} />
          重新索引
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
  return (
    <div className="space-y-5">
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <h4 className="text-sm font-semibold uppercase tracking-wide text-text-muted">处理状态</h4>
          {isProcessing && (
            <span className="text-xs text-text-muted">（自动刷新中…）</span>
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
          <h4 className="text-sm font-semibold uppercase tracking-wide text-text-muted">索引状态</h4>
          <div className="space-y-2">
            {indexes.map((idx) => (
              <div key={idx.id} className="flex items-center justify-between rounded-lg border border-border px-4 py-2 text-sm">
                <span className="text-text">{idx.indexType}</span>
                <Badge tone={idx.status === 'Completed' ? 'success' : idx.status === 'Failed' ? 'danger' : 'warning'}>
                  {getStageLabel(idx.status)}
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
