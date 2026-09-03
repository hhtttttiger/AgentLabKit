/**
 * Run Detail Page — The central execution surface.
 */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Play, FlaskConical, RotateCcw } from 'lucide-react';
import { useRunDetail, useRunEvents, useRunCost, useRunEvaluation, useRunTrace } from '../hooks';
import { AgentTraceView } from '@/shared/agent-trace/AgentTraceView';
import { StatusBadge } from '@/shared/ui/StatusBadge';
import { MetricsCard } from '@/shared/ui/MetricsCard';
import { projectRunTimeline } from '../projectors/timeline';
import { formatAdminNumber, formatAdminTime } from '@/shared/i18n/formatters';
import type { RunTimelineItem } from '../types';

type TabId = 'overview' | 'trace' | 'events' | 'cost' | 'evaluation';

export function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const { t } = useTranslation(['common', 'runs']);
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedTab = searchParams.get('tab') as TabId | null;
  const validTabs: TabId[] = ['overview', 'trace', 'events', 'cost', 'evaluation'];
  const activeTab = requestedTab && validTabs.includes(requestedTab) ? requestedTab : 'overview';
  const setActiveTab = (tab: TabId) => setSearchParams({ tab }, { replace: true });

  const { data: run, isLoading, error } = useRunDetail(runId ?? '');

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-sm text-text-muted">{t('common:states.loading')}</div>
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-sm text-error">{t('common:states.loadingFailed')}</div>
      </div>
    );
  }

  const tabs: Array<{ id: TabId; label: string }> = [
    { id: 'overview', label: t('runs:tabs.overview') },
    { id: 'trace', label: t('runs:tabs.trace') },
    { id: 'events', label: t('runs:tabs.events') },
    { id: 'cost', label: t('runs:tabs.cost') },
    { id: 'evaluation', label: t('runs:tabs.evaluation') },
  ];

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-border bg-surface px-6 py-4">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate('/runs')}
            className="rounded-[2px] p-1 text-text-muted transition hover:text-text"
          >
            <ArrowLeft size={18} />
          </button>
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h1 className="text-lg font-semibold text-text">
                {t('runs:detail.title', { id: run.id.slice(0, 8) })}
              </h1>
              <StatusBadge status={run.status} />
            </div>
            <div className="mt-1 flex items-center gap-2 text-sm text-text-secondary">
              <span className="font-medium text-text">{run.agentKey}</span>
              <span className="text-text-muted">·</span>
              {run.agentVersion && <span className="text-text-muted">v{run.agentVersion}</span>}
              {run.durationMs != null && (
                <>
                  <span className="text-text-muted">·</span>
                  <span>{formatDuration(run.durationMs)}</span>
                </>
              )}
              {run.costUsd != null && (
                <>
                  <span className="text-text-muted">·</span>
                  <span>${run.costUsd.toFixed(4)}</span>
                </>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => navigate(`/runs/${runId}/replay`)}
              className="inline-flex items-center gap-2 rounded-[2px] border border-border bg-surface px-3 py-2 text-sm font-medium text-text transition hover:bg-surface-hover"
            >
              <RotateCcw size={14} />
              {t('runs:actions.replay')}
            </button>
            <button
              type="button"
              onClick={() => navigate('/playground')}
              className="inline-flex items-center gap-2 rounded-[2px] bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90"
            >
              <Play size={14} />
              {t('runs:actions.openPlayground')}
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-border bg-surface px-6">
        <nav className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`border-b-2 px-4 py-3 text-sm font-medium transition ${
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-text-muted hover:text-text'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'overview' && <OverviewTab run={run} />}
        {activeTab === 'trace' && <TraceTab runId={run.id} />}
        {activeTab === 'events' && <EventsTab runId={run.id} />}
        {activeTab === 'cost' && <CostTab runId={run.id} />}
        {activeTab === 'evaluation' && <EvaluationTab runId={run.id} />}
      </div>
    </div>
  );
}

function OverviewTab({ run }: { run: import('../types').RunDetail }) {
  const { data, isLoading, error } = useRunEvents(run.id);
  const timeline = useMemo(() => projectRunTimeline(data?.items ?? []), [data]);
  const { t } = useTranslation(['common', 'runs']);

  return (
    <div className="px-6 py-4">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Input */}
        <div>
          <h3 className="mb-2 text-sm font-semibold text-text">{t('runs:detail.input')}</h3>
          <div className="rounded-[2px] border border-border bg-surface-subtle p-4">
            <pre className="whitespace-pre-wrap text-sm text-text-secondary">
              {run.input ?? t('runs:detail.noInput')}
            </pre>
          </div>
        </div>

        {/* Output */}
        <div>
          <h3 className="mb-2 text-sm font-semibold text-text">{t('runs:detail.output')}</h3>
          <div className="rounded-[2px] border border-border bg-surface-subtle p-4">
            <pre className="whitespace-pre-wrap text-sm text-text-secondary">
              {run.output ?? t('runs:detail.noOutput')}
            </pre>
          </div>
        </div>
      </div>
      <div className="mt-6">
        <h3 className="mb-3 text-sm font-semibold text-text">Timeline</h3>
        {isLoading ? <p className="text-sm text-text-muted">{t('common:states.loading')}</p> :
          error ? <p className="text-sm text-error">{t('common:states.loadingFailed')}</p> :
          timeline.length === 0 ? <p className="text-sm text-text-muted">{t('runs:detail.noEvents')}</p> :
          <div className="space-y-2">{timeline.map((entry) => <TimelineRow key={entry.id} item={entry} />)}</div>}
      </div>
    </div>
  );
}

function TraceTab({ runId }: { runId: string }) {
  const { t } = useTranslation(['common', 'runs']);
  const { data: trace, isLoading, error } = useRunTrace(runId);

  const emptyTitle = isLoading
    ? t('runs:detail.traceLoading')
    : error
      ? t('runs:detail.traceLoadError')
      : t('runs:detail.traceNotAvailable');
  const emptyDescription = isLoading
    ? t('runs:detail.traceLoadingDescription')
    : error
      ? t('runs:detail.traceLoadErrorDescription')
      : t('runs:detail.traceNotAvailableDescription');

  return (
    <div className="min-h-[640px] overflow-hidden rounded-[2px] border border-border bg-background-subtle/40">
      <AgentTraceView
        trace={trace ?? null}
        emptyTitle={emptyTitle}
        emptyDescription={emptyDescription}
      />
    </div>
  );
}

function EventsTab({ runId }: { runId: string }) {
  const { t } = useTranslation(['common', 'runs']);
  const { data, isLoading, error } = useRunEvents(runId);



  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-sm text-text-muted">{t('common:states.loading')}</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-sm text-error">{t('common:states.loadingFailed')}</div>
      </div>
    );
  }

  const events = data?.items ?? [];
  if (events.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-sm text-text-muted">{t('runs:detail.noEvents')}</div>
      </div>
    );
  }

  return (
    <div className="px-6 py-4">
      <div className="space-y-2">
        {events.map((event) => (
          <RawEventRow key={event.id} event={event} />
        ))}
      </div>
    </div>
  );
}

function RawEventRow({ event }: { event: import('../types').RunEvent }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="rounded-[2px] border border-border bg-surface p-3">
      <button type="button" className="flex w-full items-center justify-between text-left" onClick={() => setExpanded((value) => !value)}>
        <span className="flex items-center gap-3"><span className="font-mono text-xs text-text-muted">#{event.sequence}</span><span className="text-sm font-medium text-text">{event.type}</span></span>
        <span className="text-xs text-text-muted">{formatAdminTime(event.timestamp)}</span>
      </button>
      {expanded && <pre className="mt-3 max-h-80 overflow-auto border-t border-border pt-3 text-xs text-text-secondary">{JSON.stringify({ ...event, payload: event.payload, metadata: event.metadata }, null, 2)}</pre>}
    </div>
  );
}

function TimelineRow({ item }: { item: RunTimelineItem }) {
  const typeColors: Record<RunTimelineItem['type'], string> = {
    llm: 'bg-blue-500/10 text-blue-500',
    tool: 'bg-violet-500/10 text-violet-500',
    run: 'bg-green-500/10 text-green-500',
    error: 'bg-red-500/10 text-red-500',
    note: 'bg-gray-500/10 text-gray-500',
  };

  const statusColors: Record<string, string> = {
    ok: 'text-success',
    succeeded: 'text-success',
    running: 'text-primary',
    error: 'text-error',
    failed: 'text-error',
  };

  return (
    <div className="flex items-start gap-3 rounded-[2px] border border-border bg-surface p-3">
      <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${typeColors[item.type]}`}>
        <span className="text-xs font-bold uppercase">{item.type[0]}</span>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-text">{item.title}</span>
          <span className={`text-xs font-medium ${statusColors[item.status] ?? 'text-text-muted'}`}>
            {item.status}
          </span>
        </div>
        <div className="mt-1 flex items-center gap-2 text-xs text-text-muted">
          {item.startedAt && <span>{formatAdminTime(item.startedAt)}</span>}
          {item.durationMs != null && (
            <>
              <span>·</span>
              <span>{formatDuration(item.durationMs)}</span>
            </>
          )}
          {typeof item.metadata.eventType === 'string' && (
            <>
              <span>·</span>
              <span className="font-mono">{item.metadata.eventType}</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function CostTab({ runId }: { runId: string }) {
  const { t } = useTranslation(['common', 'runs']);
  const { data, isLoading, error } = useRunCost(runId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-sm text-text-muted">{t('common:states.loading')}</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-sm text-error">{t('common:states.loadingFailed')}</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-sm text-text-muted">{t('runs:detail.noCost')}</div>
      </div>
    );
  }

  return (
    <div className="px-6 py-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <MetricsCard label={t('runs:cost.total')} value={data.totalUsd != null ? `$${data.totalUsd.toFixed(4)}` : '—'} />
        <MetricsCard label={t('runs:cost.inputTokens')} value={data.inputTokens != null ? formatAdminNumber(data.inputTokens) : '—'} />
        <MetricsCard label={t('runs:cost.outputTokens')} value={data.outputTokens != null ? formatAdminNumber(data.outputTokens) : '—'} />
      </div>

      {data.llmCalls.length > 0 && (
        <div className="mt-6">
          <h3 className="mb-3 text-sm font-semibold text-text">{t('runs:cost.llmCalls')}</h3>
          <div className="space-y-2">
            {data.llmCalls.map((call, index) => (
              <div key={index} className="flex items-center justify-between rounded-[2px] border border-border bg-surface p-3">
                <span className="text-sm text-text">{call.modelKey}</span>
                <span className="text-sm font-medium text-text">{call.costUsd != null ? `$${call.costUsd.toFixed(4)}` : '—'}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function EvaluationTab({ runId }: { runId: string }) {
  const { t } = useTranslation(['common', 'runs']);
  const { data, isLoading, error } = useRunEvaluation(runId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-sm text-text-muted">{t('common:states.loading')}</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-sm text-error">{t('common:states.loadingFailed')}</div>
      </div>
    );
  }

  if (!data || data.overallScore === null) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <FlaskConical className="mb-4 h-12 w-12 text-text-muted" />
        <p className="text-sm text-text-muted">{t('runs:detail.noEvaluation')}</p>
      </div>
    );
  }

  return (
    <div className="px-6 py-4">
      <div className="mb-6">
        <h3 className="mb-2 text-sm font-semibold text-text">{t('runs:evaluation.overall')}</h3>
        <div className="text-3xl font-bold text-text">
          {(data.overallScore * 100).toFixed(1)}%
        </div>
      </div>

      {data.metrics.length > 0 && (
        <div>
          <h3 className="mb-3 text-sm font-semibold text-text">{t('runs:evaluation.metrics')}</h3>
          <div className="space-y-2">
            {data.metrics.map((metric) => (
              <div key={metric.name} className="flex items-center justify-between rounded-[2px] border border-border bg-surface p-3">
                <span className="text-sm text-text">{metric.name}</span>
                <span className="text-sm font-medium text-text">{metric.score != null ? `${(metric.score * 100).toFixed(1)}%` : '—'}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}
