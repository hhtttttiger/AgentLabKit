import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Bot, FlaskConical, MessageSquare, Play, Plus, AlertTriangle } from 'lucide-react';
import { useRunList } from '@/modules/runs/hooks';
import { StatusBadge } from '@/shared/ui/StatusBadge';
import { formatAdminDateTime } from '@/shared/i18n/formatters';

export function OverviewPage() {
  const { t } = useTranslation(['common', 'overview']);
  const navigate = useNavigate();
  const { data: runsData, isLoading: runsLoading } = useRunList();

  const recentRuns = runsData?.items.slice(0, 5) ?? [];
  const totalRuns = runsData?.total ?? 0;

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <div className="mx-auto w-full max-w-6xl px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-text">
            {t('overview:greeting', { time: getTimeOfDay() })}
          </h1>
          <p className="mt-2 text-text-secondary">
            {t('overview:subtitle')}
          </p>
        </div>

        {/* Quick Actions */}
        <div className="mb-8 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => navigate('/playground')}
            className="inline-flex items-center gap-2 rounded-[2px] bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition hover:bg-primary/90"
          >
            <Play size={16} />
            {t('overview:actions.testAgent')}
          </button>
          <button
            type="button"
            onClick={() => navigate('/agents')}
            className="inline-flex items-center gap-2 rounded-[2px] border border-border bg-surface px-4 py-2.5 text-sm font-medium text-text transition hover:bg-surface-hover"
          >
            <Plus size={16} />
            {t('overview:actions.createAgent')}
          </button>
        </div>

        {/* Summary Metrics */}
        <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            icon={Bot}
            label={t('overview:metrics.agents')}
            value="—"
            subtitle={t('overview:metrics.manageAgents')}
            onClick={() => navigate('/agents')}
          />
          <MetricCard
            icon={Play}
            label={t('overview:metrics.runs')}
            value={runsLoading ? '...' : String(totalRuns)}
            subtitle={totalRuns > 0 ? t('overview:metrics.totalRuns') : t('overview:metrics.noRuns')}
            onClick={() => navigate('/runs')}
          />
          <MetricCard
            icon={FlaskConical}
            label={t('overview:metrics.evaluation')}
            value="—"
            subtitle={t('overview:metrics.evaluationUnavailable')}
          />
          <MetricCard
            icon={MessageSquare}
            label={t('overview:metrics.cost')}
            value="—"
            subtitle={t('overview:metrics.costComingSoon')}
          />
        </div>

        {/* Recent Runs */}
        <div className="mb-8">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-text">
              {t('overview:recentRuns.title')}
            </h2>
            {totalRuns > 5 && (
              <button
                type="button"
                onClick={() => navigate('/runs')}
                className="text-sm font-medium text-primary hover:underline"
              >
                {t('overview:recentRuns.viewAll')}
              </button>
            )}
          </div>
          <div className="rounded-[2px] border border-border bg-surface">
            {runsLoading ? (
              <div className="flex items-center justify-center px-6 py-12">
                <div className="text-sm text-text-muted">{t('common:states.loading')}</div>
              </div>
            ) : recentRuns.length === 0 ? (
              <div className="flex items-center justify-center px-6 py-12">
                <div className="text-center">
                  <p className="text-sm text-text-muted">
                    {t('overview:recentRuns.empty')}
                  </p>
                  <button
                    type="button"
                    onClick={() => navigate('/playground')}
                    className="mt-3 text-sm font-medium text-primary hover:underline"
                  >
                    {t('overview:recentRuns.openPlayground')}
                  </button>
                </div>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {recentRuns.map((run) => (
                  <button
                    key={run.id}
                    type="button"
                    onClick={() => navigate(`/runs/${run.id}`)}
                    className="flex w-full items-center justify-between px-6 py-4 text-left transition hover:bg-surface-hover"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-3">
                        <StatusBadge status={run.status} />
                        <span className="font-medium text-text">{run.agentKey}</span>
                        <span className="font-mono text-xs text-text-muted">{run.id.slice(0, 8)}</span>
                      </div>
                      {run.durationMs != null && (
                        <span className="mt-1 text-xs text-text-muted">
                          {run.durationMs < 1000 ? `${run.durationMs}ms` : `${(run.durationMs / 1000).toFixed(2)}s`}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-text-muted">
                      {formatAdminDateTime(run.startedAt)}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Needs Attention */}
        <div>
          <h2 className="mb-4 text-lg font-semibold text-text">
            {t('overview:needsAttention.title')}
          </h2>
          <div className="rounded-[2px] border border-border bg-surface">
            <div className="flex items-center justify-center px-6 py-12">
              <div className="text-center">
                <AlertTriangle className="mx-auto mb-2 h-8 w-8 text-text-muted" />
                <p className="text-sm text-text-muted">
                  {t('overview:needsAttention.empty')}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ icon: Icon, label, value, subtitle, onClick }: {
  icon: React.ElementType;
  label: string;
  value: string;
  subtitle: string;
  onClick?: () => void;
}) {
  const Component = onClick ? 'button' : 'div';
  return (
    <Component
      onClick={onClick}
      className={`rounded-[2px] border border-border bg-surface p-4 ${onClick ? 'cursor-pointer transition hover:bg-surface-hover' : ''}`}
    >
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-[2px] bg-primary/10 text-primary">
          <Icon size={20} />
        </div>
        <div>
          <p className="text-sm text-text-muted">{label}</p>
          <p className="text-xl font-bold text-text">{value}</p>
          <p className="text-xs text-text-muted">{subtitle}</p>
        </div>
      </div>
    </Component>
  );
}

function getTimeOfDay(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'morning';
  if (hour < 18) return 'afternoon';
  return 'evening';
}
