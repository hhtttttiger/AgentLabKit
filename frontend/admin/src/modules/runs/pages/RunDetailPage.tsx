import { useTranslation } from 'react-i18next';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Play, RotateCcw } from 'lucide-react';
import { useRunDetail, useRunTrace } from '../hooks';
import { AgentTraceView } from '@/shared/agent-trace/AgentTraceView';
import { StatusBadge } from '@/shared/ui/StatusBadge';

export function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const { t } = useTranslation(['common', 'runs']);
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const tab = params.get('tab') === 'trace' ? 'trace' : 'overview';
  const { data: run, isLoading, error } = useRunDetail(runId ?? '');

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
        <button type="button" onClick={() => navigate('/playground')} className="inline-flex items-center gap-2 bg-primary px-3 py-2 text-sm text-primary-foreground"><Play size={14} />{t('runs:actions.openPlayground')}</button>
      </header>
      <nav className="flex gap-1 border-b border-border bg-surface px-6">
        {(['overview', 'trace'] as const).map((id) => <button key={id} type="button" onClick={() => setParams({ tab: id }, { replace: true })} className={`border-b-2 px-4 py-3 text-sm font-medium ${tab === id ? 'border-primary text-primary' : 'border-transparent text-text-muted'}`}>{t(`runs:tabs.${id}`)}</button>)}
      </nav>
      <div className="flex-1 overflow-y-auto">{tab === 'overview' ? <Overview run={run} /> : <Trace traceId={run.traceId} />}</div>
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

function State({ text, error = false }: { text: string; error?: boolean }) { return <div className={`flex h-full items-center justify-center text-sm ${error ? 'text-error' : 'text-text-muted'}`}>{text}</div>; }
function formatDuration(ms: number) { return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(2)}s`; }
