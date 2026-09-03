/**
 * Evaluation Overview — summary dashboard for evaluation status
 */

import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useDatasetList } from '../resources/datasets/hooks';
import { useRunList } from '../resources/configs/hooks';
import { Skeleton } from '@/shared/ui/Skeleton';
import { formatAdminDateTime } from '@/shared/i18n/formatters';

const STATUS_COLORS: Record<string, string> = {
  pending: 'text-text-muted',
  running: 'text-warning',
  completed: 'text-success',
  failed: 'text-error',
};

export function EvaluationOverviewPage() {
  const { t } = useTranslation(['evaluation']);
  const navigate = useNavigate();
  const { data: datasets, isLoading: loadingDatasets } = useDatasetList();
  const { data: runs, isLoading: loadingRuns } = useRunList();

  const datasetCount = datasets?.items?.length ?? 0;
  const runCount = runs?.length ?? 0;
  const completedRuns = runs?.filter((r) => r.status === 'completed') ?? [];
  const avgScore =
    completedRuns.length > 0
      ? completedRuns.reduce((sum, r) => sum + ((r.summary?.avgScore as number) ?? 0), 0) / completedRuns.length
      : 0;
  const recentRuns = (runs ?? []).slice(0, 5);

  if (loadingDatasets || loadingRuns) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <h2 className="text-lg font-semibold text-text">{t('evaluation:overview.title')}</h2>

      {/* Metrics */}
      <div className="grid grid-cols-3 gap-4">
        <button
          onClick={() => navigate('/evaluation/datasets')}
          className="flex flex-col items-start gap-1 rounded-lg border border-border bg-surface p-4 text-left hover:bg-surface-raised"
        >
          <span className="text-xs text-text-muted">{t('evaluation:overview.datasets')}</span>
          <span className="text-2xl font-bold text-text">{datasetCount}</span>
        </button>
        <button
          onClick={() => navigate('/evaluation/runs')}
          className="flex flex-col items-start gap-1 rounded-lg border border-border bg-surface p-4 text-left hover:bg-surface-raised"
        >
          <span className="text-xs text-text-muted">{t('evaluation:overview.totalRuns')}</span>
          <span className="text-2xl font-bold text-text">{runCount}</span>
        </button>
        <div className="flex flex-col items-start gap-1 rounded-lg border border-border bg-surface p-4">
          <span className="text-xs text-text-muted">{t('evaluation:overview.avgScore')}</span>
          <span className="text-2xl font-bold text-text">{avgScore.toFixed(3)}</span>
        </div>
      </div>

      {/* Recent runs */}
      <div>
        <h3 className="mb-3 text-sm font-medium text-text">{t('evaluation:overview.recentRuns')}</h3>
        {!recentRuns.length ? (
          <p className="text-sm text-text-muted">{t('evaluation:runs.emptyTitle')}</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-text-muted">
                <th className="pb-2 font-medium">Run ID</th>
                <th className="pb-2 font-medium text-center">{t('evaluation:runs.columns.status')}</th>
                <th className="pb-2 font-medium text-right">{t('evaluation:runs.columns.score')}</th>
                <th className="pb-2 font-medium">{t('evaluation:runs.columns.startedAt')}</th>
              </tr>
            </thead>
            <tbody>
              {recentRuns.map((r) => (
                <tr
                  key={r.id}
                  className="cursor-pointer border-b border-border-subtle last:border-0 hover:bg-surface-raised"
                  onClick={() => navigate(`/evaluation/runs/${r.id}`)}
                >
                  <td className="py-2 font-mono text-xs text-primary">#{r.id}</td>
                  <td className={`py-2 text-center text-xs font-medium ${STATUS_COLORS[r.status] || ''}`}>
                    {r.status}
                  </td>
                  <td className="py-2 text-right font-medium text-text">
                    {((r.summary?.avgScore as number) ?? 0).toFixed(3)}
                  </td>
                  <td className="py-2 text-text-secondary">
                    {formatAdminDateTime(r.createdAtUtc)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
