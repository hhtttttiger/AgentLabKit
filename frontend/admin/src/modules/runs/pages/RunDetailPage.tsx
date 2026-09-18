import { useTranslation } from 'react-i18next';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Play, RotateCcw, Database, Search } from 'lucide-react';
import { useState } from 'react';
import { useRunDetail, useRunTrace, useCaptureRun } from '../hooks';
import { useCreateDataset, useDatasetList } from '@/modules/evaluation/resources/datasets/hooks';
import { useToast } from '@/shared/ui/Toast';
import { Modal } from '@/shared/ui/Modal';
import { AgentTraceView } from '@/shared/agent-trace/AgentTraceView';
import { StatusBadge } from '@/shared/ui/StatusBadge';

export function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const { t } = useTranslation(['common', 'runs']);
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const tab = params.get('tab') === 'trace' ? 'trace' : 'overview';
  const { data: run, isLoading, error } = useRunDetail(runId ?? '');
  const [captureOpen, setCaptureOpen] = useState(false);
  const [addedDatasetId, setAddedDatasetId] = useState<string | null>(null);
  // Display context for the success banner. The capture response only carries
  // opaque identity, so the name comes from what the user already picked in
  // the modal: either the listed dataset or the one just created inline.
  const [createdDataset, setCreatedDataset] = useState<{ id: string; name: string } | null>(null);
  const captureMutation = useCaptureRun();
  const createDatasetMutation = useCreateDataset();
  const { data: datasets } = useDatasetList();
  const { toast } = useToast();

  if (isLoading) return <State text={t('common:states.loading')} />;
  if (error || !run) return <State text={t('common:states.loadingFailed')} error />;

  const addedDatasetName = datasets?.items.find((dataset) => String(dataset.id) === String(addedDatasetId))?.name
    ?? (createdDataset && createdDataset.id === addedDatasetId ? createdDataset.name : null);

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <header className="flex items-center gap-3 border-b border-border bg-surface px-6 py-4">
        <button type="button" aria-label={t('common:actions.backToList')} onClick={() => navigate('/runs')} className="p-1 text-text-muted hover:text-text"><ArrowLeft size={18} /></button>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-3"><h1 className="text-lg font-semibold text-text">{t('runs:detail.title', { id: run.id.slice(0, 8) })}</h1><StatusBadge status={run.status} /></div>
          <p className="mt-1 text-sm text-text-secondary">{run.agentKey ?? '—'}{run.agentVersion ? ` · v${run.agentVersion}` : ''}{run.durationMs != null ? ` · ${formatDuration(run.durationMs)}` : ''}</p>
        </div>
        <button type="button" onClick={() => navigate(`/runs/${run.id}/replay`)} className="inline-flex items-center gap-2 border border-border px-3 py-2 text-sm hover:bg-surface-hover"><RotateCcw size={14} />{t('runs:actions.replay')}</button>
        <button type="button" aria-label={t('runs:detail.saveAsCaseAria')} disabled={run.status !== 'completed'} onClick={() => setCaptureOpen(true)} className="inline-flex items-center gap-2 border border-border px-3 py-2 text-sm hover:bg-surface-hover disabled:cursor-not-allowed disabled:opacity-40"><Database size={14} />{t('runs:detail.saveAsCase')}</button>
        {run.traceId ? <button type="button" onClick={() => setParams({ tab: 'trace' }, { replace: true })} className="inline-flex items-center gap-2 border border-border px-3 py-2 text-sm hover:bg-surface-hover"><Search size={14} />{t('runs:actions.inspectRetrieval')}</button> : null}
        <button type="button" onClick={() => navigate(run.agentKey ? `/playground?agent=${encodeURIComponent(run.agentKey)}` : '/playground')} className="inline-flex items-center gap-2 bg-primary px-3 py-2 text-sm text-primary-foreground"><Play size={14} />{t('runs:actions.openPlayground')}</button>
      </header>
      <nav className="flex gap-1 border-b border-border bg-surface px-6">
        {(['overview', 'trace'] as const).map((id) => <button key={id} type="button" onClick={() => setParams({ tab: id }, { replace: true })} className={`border-b-2 px-4 py-3 text-sm font-medium ${tab === id ? 'border-primary text-primary' : 'border-transparent text-text-muted'}`}>{t(`runs:tabs.${id}`)}</button>)}
      </nav>
      {addedDatasetId && (
        <div role="status" className="flex flex-wrap items-center justify-between gap-3 border-b border-success/30 bg-success-subtle px-6 py-3 text-sm text-success-text">
          <span>{t('runs:detail.addedToDataset', { name: addedDatasetName ?? `#${addedDatasetId}` })}</span>
          <span className="flex gap-2">
            <button type="button" onClick={() => navigate(`/evaluation/dataset/${addedDatasetId}?evaluate=1`)} className="bg-success-text px-3 py-1.5 font-medium text-white">{t('runs:detail.evaluateDataset')}</button>
            <button type="button" onClick={() => navigate(`/evaluation/dataset/${addedDatasetId}`)} className="font-medium underline">{t('runs:detail.openDataset')}</button>
          </span>
        </div>
      )}
      <div className="flex-1 overflow-y-auto">{tab === 'overview' ? <Overview run={run} /> : <Trace traceId={run.traceId} />}</div>
      <CaptureModal open={captureOpen} datasets={datasets?.items ?? []} loading={captureMutation.isPending} creatingDataset={createDatasetMutation.isPending} error={captureMutation.error ? t('runs:detail.captureFailed') : null} onClose={() => { setCaptureOpen(false); captureMutation.reset(); }} onCreateDataset={async (name) => { const created = await createDatasetMutation.mutateAsync({ name }); setCreatedDataset({ id: created.id, name: created.name }); return created; }} onSubmit={async (datasetId, expectedOutput) => { const result = await captureMutation.mutateAsync({ runId: run.id, request: { datasetId, ...(expectedOutput ? { expectedOutput } : {}) } }); setCaptureOpen(false); setAddedDatasetId(result.datasetId); toast(t('runs:detail.toastAdded')); }} />
    </div>
  );
}

function Overview({ run }: { run: import('../types').RunDetail }) {
  const { t } = useTranslation(['runs']);
  return <div className="grid grid-cols-1 gap-6 p-6 lg:grid-cols-2">
    <Field label={t('runs:detail.input')} value={run.input ?? t('runs:detail.noInput')} />
    <Field label={t('runs:detail.output')} value={run.output ?? t('runs:detail.noOutput')} />
    <div className="border-t border-border pt-4 text-sm"><p className="text-text-muted">{t('runs:detail.sessionId')}</p><p className="mt-1 font-mono text-text">{run.sessionId ?? '—'}</p><p className="mt-3 text-text-muted">{run.status === 'completed' ? t('runs:status.completed') : t('runs:detail.ended')}</p><p className="mt-1 text-text">{run.completedAt ? new Date(run.completedAt).toLocaleString() : '—'}</p></div>
    <div className="border-t border-border pt-4 text-sm"><p className="text-text-muted">{t('runs:detail.executionFacts')}</p><div className="mt-2 grid grid-cols-2 gap-3"><Metric label={t('runs:table.duration')} value={run.durationMs == null ? t('runs:detail.unavailable') : formatDuration(run.durationMs)} /><Metric label={t('runs:tabs.trace')} value={run.traceId ? t('runs:detail.available') : t('runs:detail.unavailable')} /></div></div>
    {run.errorMessage && <div className="border-t border-border pt-4 text-sm text-error">{run.errorMessage}</div>}
  </div>;
}

function Metric({ label, value }: { label: string; value: string }) { return <div><p className="text-xs text-text-muted">{label}</p><p className="mt-1 font-medium text-text">{value}</p></div>; }

function Field({ label, value }: { label: string; value: string }) { return <div><h2 className="mb-2 text-sm font-semibold text-text">{label}</h2><pre className="whitespace-pre-wrap rounded border border-border bg-surface-subtle p-4 text-sm text-text-secondary">{value}</pre></div>; }

function Trace({ traceId }: { traceId: string | null }) {
  const { t } = useTranslation(['runs']);
  const { data, isLoading, error } = useRunTrace(traceId);
  return <div className="min-h-[640px] p-6"><AgentTraceView trace={data ?? null} emptyTitle={isLoading ? t('runs:detail.traceLoading') : error ? t('runs:detail.traceLoadError') : t('runs:detail.traceNotAvailable')} emptyDescription={traceId ? t('runs:detail.traceNotAvailableDescription') : t('runs:detail.noTraceIdentity')} /></div>;
}

function CaptureModal({ open, datasets, loading, creatingDataset, error, onClose, onCreateDataset, onSubmit }: { open: boolean; datasets: Array<{ id: string; name: string }>; loading: boolean; creatingDataset: boolean; error: string | null; onClose: () => void; onCreateDataset: (name: string) => Promise<{ id: string; name: string }>; onSubmit: (datasetId: string, expectedOutput: string) => Promise<void> }) {
  const { t } = useTranslation(['common', 'runs']);
  const [datasetId, setDatasetId] = useState('');
  const [expectedOutput, setExpectedOutput] = useState('');
  const [newDatasetName, setNewDatasetName] = useState('');
  const [createdHere, setCreatedHere] = useState<string | null>(null);
  const hasDatasets = datasets.length > 0;
  const createDataset = async () => {
    if (!newDatasetName.trim() || creatingDataset) return;
    const created = await onCreateDataset(newDatasetName.trim());
    setDatasetId(created.id);
    setCreatedHere(created.name);
    setNewDatasetName('');
  };
  return <Modal open={open} title={t('runs:detail.captureTitle')} description={t('runs:detail.captureDescription')} onClose={onClose} footer={<div className="flex justify-end gap-2"><button type="button" onClick={onClose} className="border border-border px-3 py-2 text-sm">{t('common:actions.cancel')}</button><button type="button" aria-label={t('runs:detail.addAria')} disabled={!datasetId || loading} onClick={() => onSubmit(datasetId, expectedOutput)} className="bg-primary px-3 py-2 text-sm text-primary-foreground disabled:opacity-40">{loading ? t('runs:detail.adding') : t('runs:detail.add')}</button></div>}>
    <div className="space-y-4">
      {hasDatasets ? (
        <label className="block text-sm text-text"><span className="mb-1 block font-medium">{t('runs:detail.dataset')}</span><select value={datasetId} onChange={(e) => setDatasetId(e.target.value)} className="w-full rounded border border-border bg-background px-3 py-2"><option value="">{t('runs:detail.selectDataset')}</option>{datasets.map((dataset) => <option key={dataset.id} value={dataset.id}>{dataset.name}</option>)}</select></label>
      ) : (
        <div className="space-y-2 rounded border border-dashed border-border p-4">
          <p className="text-sm text-text-secondary">{t('runs:detail.noDatasets')}</p>
          <div className="flex gap-2">
            <input aria-label={t('runs:detail.newDatasetName')} value={newDatasetName} onChange={(e) => setNewDatasetName(e.target.value)} placeholder={t('runs:detail.datasetName')} className="flex-1 rounded border border-border bg-background px-3 py-2 text-sm" />
            <button type="button" disabled={!newDatasetName.trim() || creatingDataset} onClick={createDataset} className="shrink-0 border border-border px-3 py-2 text-sm disabled:opacity-40">{creatingDataset ? t('runs:detail.creating') : t('runs:detail.createDataset')}</button>
          </div>
          {createdHere && <p role="status" className="text-sm text-success-text">{t('runs:detail.created', { name: createdHere })}</p>}
        </div>
      )}
      <label className="block text-sm text-text"><span className="mb-1 block font-medium">{t('runs:detail.expectedOutput')} <span className="font-normal text-text-muted">({t('runs:detail.optional')})</span></span><textarea value={expectedOutput} onChange={(e) => setExpectedOutput(e.target.value)} rows={4} className="w-full rounded border border-border bg-background px-3 py-2" placeholder={t('runs:detail.expectedOutputPlaceholder')} /></label>
      {error && <p role="alert" className="text-sm text-error">{error}</p>}
    </div>
  </Modal>;
}

function State({ text, error = false }: { text: string; error?: boolean }) { return <div className={`flex h-full items-center justify-center text-sm ${error ? 'text-error' : 'text-text-muted'}`}>{text}</div>; }
function formatDuration(ms: number) { return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(2)}s`; }
