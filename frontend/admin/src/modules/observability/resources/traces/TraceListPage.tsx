import { useState } from 'react';
import { useTraceList, useTraceStats } from './hooks';
import { MetricStrip } from '@/shared/ui/MetricStrip';
import { SkeletonRows } from '@/shared/ui/Skeleton';
import { EmptyState } from '@/shared/ui/EmptyState';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { Pagination } from '@/shared/ui/Pagination';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { formatDuration, formatDateTime } from '../../lib/formatters';
import type { TraceData } from '../../lib/contracts';

const TIME_RANGE_OPTIONS = [
  { days: 1, key: '24h' as const },
  { days: 7, key: '7d' as const },
  { days: 30, key: '30d' as const },
];

export function TraceListPage() {
  const { t } = useTranslation(['common', 'observability']);
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [days, setDays] = useState(7);

  const { data: result, isLoading, isError } = useTraceList({ page, pageSize, days });
  const { data: stats } = useTraceStats(days);

  const traces = result?.items ?? [];
  const total = result?.totalCount ?? 0;

  const metrics = stats
    ? [
        { label: t('observability:traces.metrics.totalTraces'), value: String(stats.totalTraces), accent: 'blue' as const },
        { label: t('observability:traces.metrics.avgLatency'), value: formatDuration(stats.avgDurationMs), accent: 'violet' as const },
        { label: t('observability:traces.metrics.totalTokens'), value: stats.totalTokens.toLocaleString(), accent: 'teal' as const },
        { label: t('observability:traces.metrics.errorCount'), value: String(stats.errorCount), accent: 'amber' as const },
      ]
    : [];

  return (
    <div className="flex flex-col gap-6 p-6 min-h-full">
      {/* Time range selector */}
      <div className="flex items-center gap-3">
        {TIME_RANGE_OPTIONS.map(({ days: d, key }) => (
          <button
            key={key}
            onClick={() => { setDays(d); setPage(1); }}
            className={`rounded-[2px] px-3 py-1 text-xs ${days === d ? 'bg-primary text-background' : 'bg-surface border border-border text-text-secondary hover:border-primary'}`}
          >
            {t(`observability:traces.timeRange.${key}`)}
          </button>
        ))}
      </div>

      {/* Stats */}
      {metrics.length > 0 && <MetricStrip items={metrics} columns={4} />}

      {/* Error */}
      {isError && (
        <InlineMessage tone="error">{t('observability:traces.loadError')}</InlineMessage>
      )}

      {/* Table */}
      <div className="flex-1 min-h-0 overflow-x-auto">
      {isLoading ? (
        <SkeletonRows columns={7} rows={5} />
      ) : !traces.length ? (
        <EmptyState title={t('observability:traces.emptyTitle')} description={t('observability:traces.emptyDescription')} />
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-text-muted">
              <th className="pb-2 font-medium w-64">{t('observability:traces.columns.traceId')}</th>
              <th className="pb-2 font-medium">{t('observability:traces.columns.agent')}</th>
              <th className="pb-2 font-medium text-center">{t('observability:traces.columns.status')}</th>
              <th className="pb-2 font-medium text-right">{t('observability:traces.columns.duration')}</th>
              <th className="pb-2 font-medium text-right">{t('observability:traces.columns.tokens')}</th>
              <th className="pb-2 font-medium text-right">{t('observability:traces.columns.spanCount')}</th>
              <th className="pb-2 font-medium pl-4">{t('observability:traces.columns.startTime')}</th>
            </tr>
          </thead>
          <tbody>
            {traces.map((tr: TraceData) => (
              <tr
                key={tr.traceId}
                className="cursor-pointer border-b border-border-subtle last:border-0 hover:bg-surface-raised"
                onClick={() => navigate(`/observability/${tr.traceId}`)}
              >
                <td className="py-2 font-mono text-xs text-primary" title={tr.traceId}>
                  <span className="cursor-pointer hover:underline" onClick={(e) => { e.stopPropagation(); navigator.clipboard.writeText(tr.traceId); }}>
                    {tr.traceId.slice(0, 32)}…
                  </span>
                </td>
                <td className="py-2 text-text-secondary">{tr.agentKey || '—'}</td>
                <td className="py-2 text-center">
                  <span className={`inline-block rounded-[2px] px-2 py-0.5 text-xs ${tr.status === 'ok' ? 'bg-success/10 text-success' : 'bg-error/10 text-error'}`}>
                    {tr.status}
                  </span>
                </td>
                <td className="py-2 text-right font-medium text-text">{formatDuration(tr.totalDurationMs)}</td>
                <td className="py-2 text-right text-text-secondary">{(tr.totalInputTokens + tr.totalOutputTokens).toLocaleString()}</td>
                <td className="py-2 text-right text-text-secondary">{tr.spanCount}</td>
                <td className="py-2 pl-4 text-text-secondary">{formatDateTime(tr.startedAtUtc)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      </div>

      {/* Pagination */}
      <Pagination
        page={page}
        pageSize={pageSize}
        totalCount={total}
        onChange={setPage}
        onPageSizeChange={(ps) => { setPageSize(ps); setPage(1); }}
      />
    </div>
  );
}
