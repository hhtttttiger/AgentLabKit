/**
 * Run Compare Page — Compare two runs side-by-side.
 */

import { useSearchParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, GitCompare } from 'lucide-react';
import { useRunDetail } from '../hooks';
import type { RunDetail } from '../types';

export function RunComparePage() {
  const [searchParams] = useSearchParams();
  const { t } = useTranslation(['common', 'runs']);
  const navigate = useNavigate();

  const runIdA = searchParams.get('baseline') ?? searchParams.get('a') ?? '';
  const runIdB = searchParams.get('candidate') ?? searchParams.get('b') ?? '';

  const { data: runA, isLoading: loadingA } = useRunDetail(runIdA);
  const { data: runB, isLoading: loadingB } = useRunDetail(runIdB);

  if (!runIdA || !runIdB) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4">
        <GitCompare className="h-12 w-12 text-text-muted" />
        <p className="text-sm text-text-muted">{t('runs:compare.selectRuns')}</p>
        <button
          type="button"
          onClick={() => navigate('/runs')}
          className="text-sm font-medium text-primary hover:underline"
        >
          {t('runs:compare.backToList')}
        </button>
      </div>
    );
  }

  if (loadingA || loadingB) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-sm text-text-muted">{t('common:states.loading')}</div>
      </div>
    );
  }

  if (!runA || !runB) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-sm text-error">{t('common:states.loadingFailed')}</div>
      </div>
    );
  }

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
          <h1 className="text-lg font-semibold text-text">{t('runs:compare.title')}</h1>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="grid grid-cols-2 gap-6">
          <RunSummaryCard run={runA} label={t('runs:compare.runA')} />
          <RunSummaryCard run={runB} label={t('runs:compare.runB')} />
        </div>

        {/* Comparison table */}
        <div className="mt-6 rounded-lg border border-border bg-surface">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-text-muted">
                <th className="px-4 py-3 font-medium">{t('runs:compare.metric')}</th>
                <th className="px-4 py-3 font-medium text-right">Run #{runA.id.slice(0, 8)}</th>
                <th className="px-4 py-3 font-medium text-right">Run #{runB.id.slice(0, 8)}</th>
                <th className="px-4 py-3 font-medium text-right">{t('runs:compare.diff')}</th>
              </tr>
            </thead>
            <tbody>
              <CompareRow
                label={t('runs:compare.duration')}
                valueA={runA.durationMs != null ? `${(runA.durationMs / 1000).toFixed(2)}s` : '—'}
                valueB={runB.durationMs != null ? `${(runB.durationMs / 1000).toFixed(2)}s` : '—'}
                numA={runA.durationMs}
                numB={runB.durationMs}
                format={(v) => `${(v / 1000).toFixed(2)}s`}
                direction="lower-is-better"
              />
              <CompareRow
                label={t('runs:compare.cost')}
                valueA={runA.costUsd != null ? `$${runA.costUsd.toFixed(4)}` : '—'}
                valueB={runB.costUsd != null ? `$${runB.costUsd.toFixed(4)}` : '—'}
                numA={runA.costUsd}
                numB={runB.costUsd}
                format={(v) => `$${v.toFixed(4)}`}
                direction="lower-is-better"
              />
              <CompareRow
                label={t('runs:compare.status')}
                valueA={runA.status}
                valueB={runB.status}
              />
              <CompareRow
                label={t('runs:compare.inputTokens')}
                valueA={runA.totalTokens?.toLocaleString() ?? '—'}
                valueB={runB.totalTokens?.toLocaleString() ?? '—'}
                numA={runA.totalTokens}
                numB={runB.totalTokens}
                format={(v) => v.toLocaleString()}
                direction="neutral"
              />
            </tbody>
          </table>
        </div>

        {/* Output comparison */}
        <div className="mt-6 grid grid-cols-2 gap-6">
          <div>
            <h3 className="mb-2 text-sm font-semibold text-text">{t('runs:compare.outputA')}</h3>
            <div className="rounded-[2px] border border-border bg-surface-subtle p-4">
              <pre className="max-h-64 overflow-auto whitespace-pre-wrap text-sm text-text-secondary">
                {runA.output ?? t('runs:detail.noOutput')}
              </pre>
            </div>
          </div>
          <div>
            <h3 className="mb-2 text-sm font-semibold text-text">{t('runs:compare.outputB')}</h3>
            <div className="rounded-[2px] border border-border bg-surface-subtle p-4">
              <pre className="max-h-64 overflow-auto whitespace-pre-wrap text-sm text-text-secondary">
                {runB.output ?? t('runs:detail.noOutput')}
              </pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function RunSummaryCard({ run, label }: { run: RunDetail; label: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <h3 className="mb-3 text-sm font-semibold text-text">{label}</h3>
      <dl className="space-y-2">
        <div className="flex justify-between">
          <dt className="text-xs text-text-muted">ID</dt>
          <dd className="font-mono text-xs text-primary">#{run.id.slice(0, 8)}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-xs text-text-muted">Agent</dt>
          <dd className="text-xs text-text">{run.agentKey}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-xs text-text-muted">Version</dt>
          <dd className="text-xs text-text">v{run.agentVersion}</dd>
        </div>
      </dl>
    </div>
  );
}

function CompareRow({
  label,
  valueA,
  valueB,
  numA,
  numB,
  format,
  direction = 'neutral',
}: {
  label: string;
  valueA: string;
  valueB: string;
  numA?: number | null;
  numB?: number | null;
  format?: (v: number) => string;
  direction?: 'higher-is-better' | 'lower-is-better' | 'neutral';
}) {
  const diff =
    numA != null && numB != null && format
      ? format(numB - numA)
      : '—';
  const diffNum = numA != null && numB != null ? numB - numA : null;
  const semantic = diffNum == null || diffNum === 0 ? 'neutral' :
    direction === 'neutral' ? 'neutral' :
      ((direction === 'higher-is-better') === (diffNum > 0) ? 'improved' : 'regressed');
  const diffClass = semantic === 'improved' ? 'text-success' : semantic === 'regressed' ? 'text-error' : 'text-text-muted';

  return (
    <tr className="border-b border-border-subtle last:border-0">
      <td className="px-4 py-3 text-text">{label}</td>
      <td className="px-4 py-3 text-right text-text-secondary">{valueA}</td>
      <td className="px-4 py-3 text-right text-text-secondary">{valueB}</td>
      <td className={`px-4 py-3 text-right font-medium ${diffClass}`}>
        {diffNum != null && diffNum > 0 ? '+' : ''}{diff}
      </td>
    </tr>
  );
}
