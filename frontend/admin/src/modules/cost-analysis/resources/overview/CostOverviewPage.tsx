import { useCostOverview, useBreakdownByModel, useCostTrend } from './hooks';
import { MetricStrip } from '@/shared/ui/MetricStrip';
import { Skeleton, SkeletonRows } from '@/shared/ui/Skeleton';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { formatCost, formatTokens, formatLatency, formatPct } from '../../lib/formatters';
import { CostTrendChart } from '../../lib/charts/CostTrendChart';
import { CostPieChart } from '../../lib/charts/CostPieChart';
import { useTranslation } from 'react-i18next';

export function CostOverviewPage() {
  const { t } = useTranslation('common');
  const overviewQuery = useCostOverview(30);
  const breakdownQuery = useBreakdownByModel(30);
  const trendQuery = useCostTrend('day', 30);

  // 等待所有查询加载完毕再渲染，避免内容闪烁
  if (overviewQuery.isLoading || breakdownQuery.isLoading || trendQuery.isLoading) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }, (_, i) => (
            <div key={i} className="rounded-[2px] border border-border bg-surface p-4">
              <Skeleton className="mb-2 h-3 w-16" />
              <Skeleton className="h-6 w-24" />
            </div>
          ))}
        </div>
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <div className="border border-border rounded-[2px] bg-surface px-6 py-4">
            <Skeleton className="mb-3 h-3 w-20" />
            <Skeleton className="h-48 w-full" />
          </div>
          <div className="border border-border rounded-[2px] bg-surface px-6 py-4">
            <Skeleton className="mb-3 h-3 w-20" />
            <Skeleton className="h-48 w-full" />
          </div>
        </div>
        <SkeletonRows columns={6} rows={5} />
      </div>
    );
  }

  // 任一查询出错时显示错误状态
  if (overviewQuery.isError) {
    return (
      <div className="p-6">
        <InlineMessage tone="error">
          {overviewQuery.error?.message ?? t('modules.costAnalysis.overview.error')}
        </InlineMessage>
      </div>
    );
  }

  const overview = overviewQuery.data!;
  const breakdown = breakdownQuery.data;
  const trend = trendQuery.data;

  const metrics = [
    { label: t('modules.costAnalysis.overview.totalSpend'), value: formatCost(overview.totalSpend), hint: formatPct(overview.spendChangePct), accent: 'blue' as const },
    { label: t('modules.costAnalysis.overview.totalRequests'), value: String(overview.totalRequests), hint: `前 ${formatCost(overview.prevTotalSpend)}`, accent: 'violet' as const },
    { label: t('modules.costAnalysis.overview.totalTokens'), value: formatTokens(overview.totalTokens), accent: 'teal' as const },
    { label: t('modules.costAnalysis.overview.avgLatency'), value: formatLatency(overview.avgLatencyMs), accent: 'amber' as const },
  ];

  return (
    <div className="flex flex-col gap-6 p-6">
      <MetricStrip items={metrics} columns={4} />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {/* 成本趋势 */}
        <div className="border border-border rounded-[2px] bg-surface px-6 py-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
            {t('modules.costAnalysis.overview.costTrend')}
          </h3>
          {trend && <CostTrendChart data={trend} />}
        </div>

        {/* 模型分布 */}
        <div className="border border-border rounded-[2px] bg-surface px-6 py-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
            {t('modules.costAnalysis.overview.modelDistribution')}
          </h3>
          {breakdown && <CostPieChart data={breakdown.slice(0, 6)} />}
        </div>
      </div>

      {/* Top 模型列表 */}
      {overview.topModels.length > 0 && (
        <div className="border border-border rounded-[2px] bg-surface px-6 py-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
            {t('modules.costAnalysis.overview.topModels')}
          </h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-text-muted">
                <th className="pb-2 font-medium">模型</th>
                <th className="pb-2 font-medium text-right">请求数</th>
                <th className="pb-2 font-medium text-right">输入 Token</th>
                <th className="pb-2 font-medium text-right">输出 Token</th>
                <th className="pb-2 font-medium text-right">花费</th>
                <th className="pb-2 font-medium text-right">平均延迟</th>
              </tr>
            </thead>
            <tbody>
              {overview.topModels.map((m) => (
                <tr key={m.scope} className="border-b border-border-subtle last:border-0">
                  <td className="py-2 font-medium text-text">{m.scope}</td>
                  <td className="py-2 text-right text-text-secondary">{m.totalRequests.toLocaleString()}</td>
                  <td className="py-2 text-right text-text-secondary">{formatTokens(m.totalInputTokens)}</td>
                  <td className="py-2 text-right text-text-secondary">{formatTokens(m.totalOutputTokens)}</td>
                  <td className="py-2 text-right font-medium text-text">{formatCost(m.totalEstimatedCost)}</td>
                  <td className="py-2 text-right text-text-secondary">{formatLatency(m.avgLatencyMs)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
