import { useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTraceDetail } from './hooks';
import { TraceWaterfallChart } from './TraceWaterfallChart';
import { MetricStrip } from '@/shared/ui/MetricStrip';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { formatDuration, formatSpanKind, getSpanKindColor } from '../../lib/formatters';
import { useTranslation } from 'react-i18next';
import type { SpanData } from '../../lib/contracts';

export function TraceDetailPage() {
  const { t } = useTranslation(['common', 'observability']);
  const { traceId } = useParams<{ traceId: string }>();
  const navigate = useNavigate();
  const [selectedSpanId, setSelectedSpanId] = useState<string | null>(null);

  const { data: detail, isLoading, isError } = useTraceDetail(traceId || '');

  const selectedSpan = useMemo(
    () => {
      if (!detail || !selectedSpanId) return null;
      return detail.spans.find(s => s.spanId === selectedSpanId) ?? null;
    },
    [selectedSpanId, detail],
  );

  if (isLoading) {
    return <div className="p-6 text-text-muted">{t('states.loading')}</div>;
  }

  if (isError || !detail) {
    return (
      <div className="p-6">
        <InlineMessage tone="error">{t('observability:traces.detailLoadError')}</InlineMessage>
      </div>
    );
  }

  const { trace, spans } = detail;
  const totalTokens = trace.totalInputTokens + trace.totalOutputTokens;

  const metrics = [
    { label: t('observability:traces.columns.duration'), value: formatDuration(trace.totalDurationMs), accent: 'blue' as const },
    { label: t('observability:traces.metrics.totalTokens'), value: totalTokens.toLocaleString(), accent: 'violet' as const },
    { label: t('observability:traces.columns.spanCount'), value: String(trace.spanCount), accent: 'teal' as const },
    { label: t('observability:traces.columns.status'), value: trace.status, accent: (trace.status === 'ok' ? 'teal' : 'amber') as 'teal' | 'amber' },
  ];

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Back + header */}
      <div className="flex items-center gap-4">
        <button onClick={() => navigate('/observability')} className="text-sm text-text-secondary hover:text-primary">
          {t('observability:traces.detail.backToList')}
        </button>
        <h2 className="font-mono text-sm text-text-muted">
          Trace: {trace.traceId}
        </h2>
        {trace.agentKey && (
          <span className="rounded-[2px] bg-primary/10 px-2 py-0.5 text-xs text-primary">
            {trace.agentKey}
          </span>
        )}
      </div>

      <MetricStrip items={metrics} columns={4} compact />

      {/* Waterfall chart */}
      <div className="overflow-x-auto rounded-[2px] border border-border bg-surface px-4 py-4">
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
          {t('observability:traces.detail.waterfall')}
        </h3>
        <TraceWaterfallChart
          spans={spans}
          traceStart={trace.startedAtUtc}
          emptyText={t('observability:traces.detail.noSpanData')}
        />
      </div>

      {/* Span list */}
      <div className="overflow-x-auto rounded-[2px] border border-border bg-surface">
        <div className="px-6 py-3 text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
          {t('observability:traces.detail.spanList')} ({spans.length})
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-text-muted">
              <th className="px-6 pb-2 font-medium">{t('observability:traces.detail.columns.kind')}</th>
              <th className="pb-2 font-medium">{t('observability:traces.detail.columns.name')}</th>
              <th className="pb-2 font-medium text-center">{t('observability:traces.detail.columns.status')}</th>
              <th className="pb-2 font-medium text-right">{t('observability:traces.detail.columns.duration')}</th>
              <th className="pb-2 font-medium text-right">{t('observability:traces.detail.columns.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {spans.map((span) => (
              <tr
                key={span.spanId}
                className="cursor-pointer border-b border-border-subtle last:border-0 hover:bg-surface-raised"
                onClick={() => setSelectedSpanId(selectedSpanId === span.spanId ? null : span.spanId)}
              >
                <td className="px-6 py-2">
                  <span
                    className="inline-block rounded-[2px] px-2 py-0.5 text-xs"
                    style={{ backgroundColor: `rgb(${getSpanKindColor(span.spanKind)} / 0.15)`, color: `rgb(${getSpanKindColor(span.spanKind)})` }}
                  >
                    {formatSpanKind(span.spanKind, span.attributes)}
                  </span>
                </td>
                <td className="py-2 text-text">{span.name}</td>
                <td className="py-2 text-center">
                  <span className={`text-xs ${span.status === 'ok' ? 'text-success' : 'text-error'}`}>
                    {span.status}
                  </span>
                </td>
                <td className="py-2 text-right font-medium text-text">{formatDuration(span.durationMs)}</td>
                <td className="py-2 text-right">
                  <button className="text-xs text-primary hover:underline">
                    {selectedSpanId === span.spanId
                      ? t('observability:traces.detail.collapse')
                      : t('observability:traces.detail.expand')}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Selected span detail */}
        {selectedSpan && (
          <div className="border-t border-border bg-background-sunken px-6 py-4">
            <h4 className="mb-2 text-xs font-semibold text-text-muted">{t('observability:traces.detail.spanAttributes')}</h4>
            <pre className="max-h-48 overflow-auto rounded-[2px] bg-background p-3 text-xs text-text-secondary">
              {JSON.stringify({ ...selectedSpan, attributes: selectedSpan.attributes }, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
