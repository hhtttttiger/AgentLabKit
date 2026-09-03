import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Play, Search } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useRunList } from '../hooks';
import { EmptyState } from '@/shared/ui/EmptyState';
import { SkeletonRows } from '@/shared/ui/Skeleton';
import { StatusBadge } from '@/shared/ui/StatusBadge';
import type { RunSummary } from '../types';

const PAGE_SIZE = 20;

export function RunsListPage() {
  const { t } = useTranslation(['common', 'runs']);
  const [page, setPage] = useState(0);
  const offset = page * PAGE_SIZE;
  const { data, isLoading, isFetching, error } = useRunList({ limit: PAGE_SIZE, offset });
  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const hasPrevious = offset > 0;
  const hasNext = offset + items.length < total;

  if (isLoading) return <div className="p-6"><SkeletonRows columns={5} rows={6} /></div>;
  if (error) return <div role="alert" className="p-6 text-sm text-error">{t('common:states.loadingFailed')}</div>;
  if (!items.length) return <div className="flex h-full flex-col items-center justify-center gap-4 p-6 text-center"><Search className="h-12 w-12 text-text-muted" /><EmptyState title={t('runs:title')} description="Completed and in-progress Agent Runs will appear here." /><Link to="/playground" className="inline-flex items-center gap-2 bg-primary px-3 py-2 text-sm text-primary-foreground"><Play size={14} />{t('runs:openPlayground')}</Link></div>;

  return <div className="flex flex-col gap-4 p-6">
    <div><h1 className="text-lg font-semibold text-text">{t('runs:title')}</h1><p className="mt-1 text-sm text-text-secondary">Recent durable Runs owned by your account.</p></div>
    <div className="overflow-x-auto border border-border bg-surface" aria-busy={isFetching}>
      <table className="w-full text-sm"><thead><tr className="border-b border-border text-left text-text-muted"><th className="px-4 py-3 font-medium">Run ID</th><th className="px-4 py-3 font-medium">Target</th><th className="px-4 py-3 font-medium">Status</th><th className="px-4 py-3 font-medium">Started</th><th className="px-4 py-3 text-right font-medium">Duration</th></tr></thead><tbody>{items.map((run) => <RunRow key={run.id} run={run} />)}</tbody></table>
    </div>
    <nav className="flex items-center justify-between text-sm" aria-label="Run list pagination">
      <button type="button" onClick={() => setPage((current) => current - 1)} disabled={!hasPrevious || isFetching} className="border border-border px-3 py-1.5 text-text-secondary hover:bg-surface-raised disabled:cursor-not-allowed disabled:opacity-40">Previous</button>
      <span className="text-text-secondary" aria-live="polite">Page {page + 1}</span>
      <button type="button" onClick={() => setPage((current) => current + 1)} disabled={!hasNext || isFetching} className="border border-border px-3 py-1.5 text-text-secondary hover:bg-surface-raised disabled:cursor-not-allowed disabled:opacity-40">Next</button>
    </nav>
  </div>;
}

function RunRow({ run }: { run: RunSummary }) {
  return <tr className="border-b border-border-subtle last:border-0 hover:bg-surface-raised"><td className="px-4 py-3"><Link className="font-mono text-xs text-primary hover:underline" to={`/runs/${encodeURIComponent(run.id)}`}>{run.id}</Link></td><td className="px-4 py-3 text-text">{run.agentKey ?? '—'}{run.agentVersion ? ` · v${run.agentVersion}` : ''}</td><td className="px-4 py-3"><StatusBadge status={run.status} /></td><td className="px-4 py-3 text-text-secondary">{run.startedAt ? new Date(run.startedAt).toLocaleString() : '—'}</td><td className="px-4 py-3 text-right text-text-secondary">{run.durationMs == null ? '—' : formatDuration(run.durationMs)}</td></tr>;
}
function formatDuration(ms: number) { return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(2)}s`; }
