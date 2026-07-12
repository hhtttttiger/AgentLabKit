import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useModelOptions } from '@/modules/model-management/options/hooks';
import { EmptyState } from '@/shared/ui/EmptyState';
import { MetricStrip } from '@/shared/ui/MetricStrip';
import { SkeletonCards } from '@/shared/ui/Skeleton';
import { buildCardDisplayNameMap, toMonitoringOverview } from '../lib/mappers';
import { useMonitoringOverview } from '../resources/usage/hooks';
import { ModelSummaryCard } from '../components/ModelSummaryCard';
import { formatCompact, formatLatency } from '../lib/formatters';

export function ModelMonitoringOverviewPage() {
  const { t } = useTranslation(['common', 'modelMonitoring']);
  const modelOptionsQuery = useModelOptions();
  const overviewQuery = useMonitoringOverview({});

  const cardDisplayNames = buildCardDisplayNameMap(modelOptionsQuery.data);
  const data = overviewQuery.data
    ? toMonitoringOverview(overviewQuery.data, cardDisplayNames)
    : null;
  const isLoading = overviewQuery.isLoading || modelOptionsQuery.isLoading;

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="space-y-6 pb-3">
        <MetricStrip
          items={[
            { label: t('modelMonitoring:overview.metrics.totalRequests'), value: data ? formatCompact(data.totalRequests) : '-', hint: t('modelMonitoring:overview.hints.totalRequests'), accent: 'blue' },
            { label: t('modelMonitoring:overview.metrics.totalTokens'), value: data ? formatCompact(data.totalTokens) : '-', hint: t('modelMonitoring:overview.hints.totalTokens'), accent: 'violet' },
            { label: t('modelMonitoring:overview.metrics.averageLatency'), value: data ? formatLatency(data.averageLatencyMs) : '-', hint: t('modelMonitoring:overview.hints.averageLatency'), accent: 'teal' },
            { label: t('modelMonitoring:overview.metrics.totalErrors'), value: data ? formatCompact(data.totalErrors) : '-', hint: t('modelMonitoring:overview.hints.totalErrors'), accent: 'amber' },
          ]}
        />

        {isLoading ? (
          <SkeletonCards />
        ) : !data?.modelSummaries.length ? (
          <EmptyState title={t('modelMonitoring:overview.emptyTitle')} description={t('modelMonitoring:overview.emptyDescription')} />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {data.modelSummaries.map((card) => (
              <Link
                key={card.modelKey}
                to={`/model-monitoring/usage?modelKey=${encodeURIComponent(card.modelKey)}`}
                className="block"
              >
                <ModelSummaryCard card={card} />
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
