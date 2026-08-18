import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import { EmptyState } from '@/shared/ui/EmptyState';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { MetricStrip } from '@/shared/ui/MetricStrip';
import { SkeletonRows } from '@/shared/ui/Skeleton';
import { formatDateTime, formatDuration } from '../../lib/formatters';
import type { TraceData, TraceStatus } from '../../lib/contracts';
import { useIngestionHealth, useTraceList, useTraceStats } from './hooks';

const PAGE_SIZE = 20;

export function TraceListPage() {
  const { t } = useTranslation(['common', 'observability']);
  const navigate = useNavigate();
  const [cursorStack, setCursorStack] = useState<Array<string | undefined>>([undefined]);
  const [agentKey, setAgentKey] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [status, setStatus] = useState<TraceStatus | ''>('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const cursor = cursorStack[cursorStack.length - 1];
  const params = useMemo(() => ({
    cursor,
    limit: PAGE_SIZE,
    agent_key: agentKey || undefined,
    session_id: sessionId || undefined,
    status: status || undefined,
    from_date: fromDate ? new Date(fromDate).toISOString() : undefined,
    to_date: toDate ? new Date(toDate).toISOString() : undefined,
  }), [agentKey, cursor, fromDate, sessionId, status, toDate]);

  const { data: result, isLoading, isError } = useTraceList(params);
  const { data: stats } = useTraceStats(7);
  const { data: health } = useIngestionHealth();
  const traces = result?.items ?? [];

  const resetCursor = () => setCursorStack([undefined]);
  const metrics = stats ? [
    { label: t('observability:traces.metrics.totalTraces'), value: String(stats.totalTraces), accent: 'blue' as const },
    { label: 'P95', value: formatDuration(stats.p95DurationMs), accent: 'violet' as const },
    { label: t('observability:traces.metrics.totalTokens'), value: stats.totalTokens.toLocaleString(), accent: 'teal' as const },
    { label: 'Errors / timeout / cancel', value: `${stats.errorCount} / ${stats.timeoutCount} / ${stats.cancelledCount}`, accent: 'amber' as const },
  ] : [];

  return (
    <div className="flex min-h-full flex-col gap-6 p-6">
      {metrics.length > 0 && <MetricStrip items={metrics} columns={4} />}

      <div className="grid gap-3 rounded-[2px] border border-border bg-surface p-3 text-xs text-text-secondary md:grid-cols-2">
        <div>
          Buffer: traces {health?.publisher.activeTraces ?? '—'}, spans {health?.publisher.bufferedSpans ?? '—'},
          dropped {health?.publisher.bufferOverflowDropped ?? '—'} ·
          Publisher: queued {health?.publisher.queueDepth ?? '—'}, published {health?.publisher.published ?? '—'},
          dropped <span className={health?.publisher.dropped ? 'text-error' : ''}>{health?.publisher.dropped ?? '—'}</span>
        </div>
        <div>
          Trace worker: {health?.queue?.available ? 'available' : 'unavailable'}, consumers {health?.queue?.consumers ?? '—'}, backlog {health?.queue?.backlog ?? '—'}, pending {health?.queue?.pending ?? '—'},
          delayed {health?.queue?.delayed ?? '—'}, DLQ {health?.queue?.deadLetter ?? '—'}
        </div>
        {Object.entries(health?.workerTasks ?? {}).map(([name, task]) => (
          <div key={name}>
            {name}: {task.available ? 'available' : 'unavailable'}, consumers {task.consumers}, backlog {task.backlog}, pending {task.pending},
            failures/DLQ {task.deadLetter}
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        <input value={agentKey} onChange={(event) => { setAgentKey(event.target.value); resetCursor(); }} placeholder="Agent key" className="rounded-[2px] border border-border bg-surface px-3 py-1.5 text-sm" />
        <input value={sessionId} onChange={(event) => { setSessionId(event.target.value); resetCursor(); }} placeholder="Session ID" className="rounded-[2px] border border-border bg-surface px-3 py-1.5 text-sm" />
        <select value={status} onChange={(event) => { setStatus(event.target.value as TraceStatus | ''); resetCursor(); }} className="rounded-[2px] border border-border bg-surface px-3 py-1.5 text-sm">
          <option value="">All statuses</option>
          <option value="ok">ok</option>
          <option value="error">error</option>
          <option value="timeout">timeout</option>
          <option value="cancelled">cancelled</option>
        </select>
        <input type="datetime-local" value={fromDate} onChange={(event) => { setFromDate(event.target.value); resetCursor(); }} aria-label="Started after" className="rounded-[2px] border border-border bg-surface px-3 py-1.5 text-sm" />
        <input type="datetime-local" value={toDate} onChange={(event) => { setToDate(event.target.value); resetCursor(); }} aria-label="Started before" className="rounded-[2px] border border-border bg-surface px-3 py-1.5 text-sm" />
      </div>

      {isError && <InlineMessage tone="error">{t('observability:traces.loadError')}</InlineMessage>}

      <div className="min-h-0 flex-1 overflow-x-auto">
        {isLoading ? <SkeletonRows columns={8} rows={5} /> : !traces.length ? (
          <EmptyState title={t('observability:traces.emptyTitle')} description={t('observability:traces.emptyDescription')} />
        ) : (
          <table className="w-full text-sm">
            <thead><tr className="border-b border-border text-left text-text-muted">
              <th className="w-64 pb-2 font-medium">{t('observability:traces.columns.traceId')}</th>
              <th className="pb-2 font-medium">{t('observability:traces.columns.agent')}</th>
              <th className="pb-2 text-center font-medium">{t('observability:traces.columns.status')}</th>
              <th className="pb-2 text-right font-medium">{t('observability:traces.columns.duration')}</th>
              <th className="pb-2 text-right font-medium">{t('observability:traces.columns.tokens')}</th>
              <th className="pb-2 text-right font-medium">Cost</th>
              <th className="pb-2 text-right font-medium">Spans / dropped</th>
              <th className="pb-2 pl-4 font-medium">{t('observability:traces.columns.startTime')}</th>
            </tr></thead>
            <tbody>{traces.map((trace: TraceData) => (
              <tr key={trace.traceId} className="cursor-pointer border-b border-border-subtle hover:bg-surface-raised" onClick={() => navigate(`/observability/${trace.traceId}`)}>
                <td className="py-2 font-mono text-xs text-primary" title={trace.traceId}>{trace.traceId}</td>
                <td className="py-2 text-text-secondary">{trace.agentKey || '—'}</td>
                <td className="py-2 text-center"><span className={`rounded-[2px] px-2 py-0.5 text-xs ${trace.status === 'ok' ? 'bg-success/10 text-success' : 'bg-error/10 text-error'}`}>{trace.status}</span></td>
                <td className="py-2 text-right">{formatDuration(trace.totalDurationMs)}</td>
                <td className="py-2 text-right text-text-secondary">{(trace.totalInputTokens + trace.totalOutputTokens).toLocaleString()}</td>
                <td className="py-2 text-right text-text-secondary">${trace.totalEstimatedCost.toFixed(6)}</td>
                <td className="py-2 text-right text-text-secondary">{trace.spanCount} / <span className={trace.droppedSpanCount ? 'text-error' : ''}>{trace.droppedSpanCount}</span></td>
                <td className="py-2 pl-4 text-text-secondary">{formatDateTime(trace.startedAtUtc)}</td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </div>

      <div className="flex justify-end gap-2">
        <button disabled={cursorStack.length === 1} onClick={() => setCursorStack((items) => items.slice(0, -1))} className="rounded-[2px] border border-border px-3 py-1 text-sm disabled:opacity-40">Previous</button>
        <button disabled={!result?.nextCursor} onClick={() => result?.nextCursor && setCursorStack((items) => [...items, result.nextCursor!])} className="rounded-[2px] border border-border px-3 py-1 text-sm disabled:opacity-40">Next</button>
      </div>
    </div>
  );
}
