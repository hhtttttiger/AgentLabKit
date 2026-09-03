/**
 * Runs List Page — All run facts in one place.
 */

import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Play, Search } from 'lucide-react';
import { useRunList } from '../hooks';
import type { RunSummary } from '../types';
import { StatusBadge as SharedStatusBadge } from '@/shared/ui/StatusBadge';

export function RunsListPage() {
  const { t } = useTranslation(['common', 'runs']);
  const navigate = useNavigate();
  const { data, isLoading, error } = useRunList();

  const runs = data?.items ?? [];

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Page Header */}
      <div className="border-b border-border bg-surface px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-text">{t('runs:title')}</h1>
            <p className="mt-1 text-sm text-text-secondary">{t('runs:subtitle')}</p>
          </div>
          <button
            type="button"
            onClick={() => navigate('/playground')}
            className="inline-flex items-center gap-2 rounded-[2px] bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90"
          >
            <Play size={14} />
            {t('runs:openPlayground')}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-sm text-text-muted">{t('common:states.loading')}</div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-sm text-error">{t('common:states.loadingFailed')}</div>
          </div>
        ) : runs.length === 0 ? (
          <EmptyState />
        ) : (
          <RunsTable runs={runs} onRunClick={(runId) => navigate(`/runs/${runId}`)} />
        )}
      </div>
    </div>
  );
}

function EmptyState() {
  const { t } = useTranslation(['runs']);
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center justify-center py-12">
      <Search className="mb-4 h-12 w-12 text-text-muted" />
      <h3 className="text-sm font-semibold text-text">{t('runs:empty.title')}</h3>
      <p className="mt-2 text-sm text-text-secondary">{t('runs:empty.description')}</p>
      <button
        type="button"
        onClick={() => navigate('/playground')}
        className="mt-4 inline-flex items-center gap-2 rounded-[2px] bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90"
      >
        <Play size={14} />
        {t('runs:empty.openPlayground')}
      </button>
    </div>
  );
}

function RunsTable({ runs, onRunClick }: { runs: RunSummary[]; onRunClick: (runId: string) => void }) {
  const { t } = useTranslation(['runs']);

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-border">
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-text-muted">
              {t('runs:table.status')}
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-text-muted">
              {t('runs:table.agent')}
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-text-muted">
              {t('runs:table.duration')}
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-text-muted">
              {t('runs:table.cost')}
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-text-muted">
              {t('runs:table.evaluation')}
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-text-muted">
              {t('runs:table.time')}
            </th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr
              key={run.id}
              className="cursor-pointer border-b border-border/50 transition hover:bg-surface-hover"
              onClick={() => onRunClick(run.id)}
            >
              <td className="px-4 py-3">
                <SharedStatusBadge status={run.status} />
              </td>
              <td className="px-4 py-3">
                <div className="text-sm font-medium text-text">{run.agentKey}</div>
                <div className="text-xs text-text-muted">v{run.agentVersion}</div>
              </td>
              <td className="px-4 py-3 text-sm text-text-secondary">
                {run.durationMs != null ? formatDuration(run.durationMs) : '—'}
              </td>
              <td className="px-4 py-3 text-sm text-text-secondary">
                {run.costUsd != null ? `$${run.costUsd.toFixed(4)}` : '—'}
              </td>
              <td className="px-4 py-3 text-sm text-text-secondary">
                {run.evaluationScore != null ? `${(run.evaluationScore * 100).toFixed(1)}%` : '—'}
              </td>
              <td className="px-4 py-3 text-sm text-text-muted">
                {formatRelativeTime(run.startedAt)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

function formatRelativeTime(isoString: string | null): string {
  if (!isoString) return '—';
  const now = new Date();
  const date = new Date(isoString);
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMinutes < 1) return 'just now';
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}
