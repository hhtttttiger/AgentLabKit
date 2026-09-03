import { useTranslation } from 'react-i18next';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Play, RotateCcw, Database } from 'lucide-react';
import { useState } from 'react';
import { useRunDetail, useRunTrace, useCaptureRun } from '../hooks';
import { useDatasetList } from '@/modules/evaluation/resources/datasets/hooks';
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
  const captureMutation = useCaptureRun();
  const { data: datasets } = useDatasetList();
  const { toast } = useToast();

  if (isLoading) return <State text={t('common:states.loading')} />;
  if (error || !run) return <State text={t('common:states.loadingFailed')} error />;

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <header className="flex items-center gap-3 border-b border-border bg-surface px-6 py-4">
        <button type="button" aria-label="Back" onClick={() => navigate('/runs')} className="p-1 text-text-muted hover:text-text"><ArrowLeft size={18} /></button>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-3"><h1 className="text-lg font-semibold text-text">{t('runs:detail.title', { id: run.id.slice(0, 8) })}</h1><StatusBadge status={run.status} /></div>
          <p className="mt-1 text-sm text-text-secondary">{run.agentKey ?? '—'}{run.agentVersion ? ` · v${run.agentVersion}` : ''}{run.durationMs != null ? ` · ${formatDuration(run.durationMs)}` : ''}</p>
        </div>
        <button type="button" onClick={() => navigate(`/runs/${run.id}/replay`)} className="inline-flex items-center gap-2 border border-border px-3 py-2 text-sm hover:bg-surface-hover"><RotateCcw size={14} />{t('runs:actions.replay')}</button>
        <button type="button" disabled={run.status !== 'completed'} onClick={() => setCaptureOpen(true)} className="inline-flex items-center gap-2 border border-border px-3 py-2 text-sm hover:bg-surface-hover disabled:cursor-not-allowed disabled:opacity-40"><Database size={14} />Capture</button>
        <button type="button" onClick={() => navigate(run.agentKey ? `/playground?agent=${encodeURIComponent(run.agentKey)}` : '/playground')} className="inline-flex items-center gap-2 bg-primary px-3 py-2 text-sm text-primary-foreground"><Play size={14} />{t('runs:actions.openPlayground')}</button>
      </header>
      <nav className="flex gap-1 border-b border-border bg-surface px-6">
        {(['overview', 'trace'] as const).map((id) => <button key={id} type="button" onClick={() => setParams({ tab: id }, { replace: true })} className={`border-b-2 px-4 py-3 text-sm font-medium ${tab === id ? 'border-primary text-primary' : 'border-transparent text-text-muted'}`}>{t(`runs:tabs.${id}`)}</button>)}
      </nav>
      <div className="flex-1 overflow-y-auto">{tab === 'overview' ? <Overview run={run} /> : <Trace traceId={run.traceId} />}</div>
      <CaptureModal open={captureOpen} datasets={datasets?.items ?? []} loading={captureMutation.isPending} error={captureMutation.error ? 'Capture failed. Please try again.' : null} onClose={() => { setCaptureOpen(false); captureMutation.reset(); }} onSubmit={async (datasetId, expectedOutput) => { const result = await captureMutation.mutateAsync({ runId: run.id, request: { datasetId, ...(expectedOutput ? { expectedOutput } : {}) } }); setCaptureOpen(false); toast(`Captured as DatasetExample ${result.exampleId}`); }} />
    </div>
  );
}

function Overview({ run }: { run: import('../types').RunDetail }) {
  const { t } = useTranslation(['runs']);
  return <div className="grid grid-cols-1 gap-6 p-6 lg:grid-cols-2">
    <Field label={t('runs:detail.input')} value={run.input ?? t('runs:detail.noInput')} />
    <Field label={t('runs:detail.output')} value={run.output ?? t('runs:detail.noOutput')} />
    <div className="border-t border-border pt-4 text-sm"><p className="text-text-muted">Session ID</p><p className="mt-1 font-mono text-text">{run.sessionId ?? '—'}</p><p className="mt-3 text-text-muted">Completed</p><p className="mt-1 text-text">{run.completedAt ? new Date(run.completedAt).toLocaleString() : '—'}</p></div>
    {run.errorMessage && <div className="border-t border-border pt-4 text-sm text-error">{run.errorMessage}</div>}
  </div>;
}

function Field({ label, value }: { label: string; value: string }) { return <div><h2 className="mb-2 text-sm font-semibold text-text">{label}</h2><pre className="whitespace-pre-wrap rounded border border-border bg-surface-subtle p-4 text-sm text-text-secondary">{value}</pre></div>; }

function Trace({ traceId }: { traceId: string | null }) {
  const { t } = useTranslation(['runs']);
  const { data, isLoading, error } = useRunTrace(traceId);
  return <div className="min-h-[640px] p-6"><AgentTraceView trace={data ?? null} emptyTitle={isLoading ? t('runs:detail.traceLoading') : error ? t('runs:detail.traceLoadError') : t('runs:detail.traceNotAvailable')} emptyDescription={traceId ? t('runs:detail.traceNotAvailableDescription') : 'This Run has no trace identity.'} /></div>;
}

function CaptureModal({ open, datasets, loading, error, onClose, onSubmit }: { open: boolean; datasets: Array<{ id: string; name: string }>; loading: boolean; error: string | null; onClose: () => void; onSubmit: (datasetId: number, expectedOutput: string) => Promise<void> }) {
  const [datasetId, setDatasetId] = useState('');
  const [expectedOutput, setExpectedOutput] = useState('');
  return <Modal open={open} title="Capture Run" description="Save this completed Run as a DatasetExample. Expected output is optional and remains empty unless you provide it." onClose={onClose} footer={<div className="flex justify-end gap-2"><button type="button" onClick={onClose} className="border border-border px-3 py-2 text-sm">Cancel</button><button type="button" disabled={!datasetId || loading} onClick={() => onSubmit(Number(datasetId), expectedOutput)} className="bg-primary px-3 py-2 text-sm text-primary-foreground disabled:opacity-40">{loading ? 'Capturing…' : 'Capture Run'}</button></div>}>
    <div className="space-y-4"><label className="block text-sm text-text"><span className="mb-1 block font-medium">Dataset</span><select value={datasetId} onChange={(e) => setDatasetId(e.target.value)} className="w-full rounded border border-border bg-background px-3 py-2"><option value="">Select a dataset</option>{datasets.map((dataset) => <option key={dataset.id} value={dataset.id}>{dataset.name}</option>)}</select></label><label className="block text-sm text-text"><span className="mb-1 block font-medium">Expected output <span className="font-normal text-text-muted">(optional)</span></span><textarea value={expectedOutput} onChange={(e) => setExpectedOutput(e.target.value)} rows={4} className="w-full rounded border border-border bg-background px-3 py-2" placeholder="Leave empty to keep this unset" /></label>{error && <p role="alert" className="text-sm text-error">{error}</p>}</div>
  </Modal>;
}

function State({ text, error = false }: { text: string; error?: boolean }) { return <div className={`flex h-full items-center justify-center text-sm ${error ? 'text-error' : 'text-text-muted'}`}>{text}</div>; }
function formatDuration(ms: number) { return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(2)}s`; }
