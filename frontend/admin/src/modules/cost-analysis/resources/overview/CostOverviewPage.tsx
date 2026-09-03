import { useCostOverview, useBreakdownByModel, useCostTrend } from './hooks';
import { MetricStrip } from '@/shared/ui/MetricStrip';
import { Skeleton, SkeletonRows } from '@/shared/ui/Skeleton';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { formatCost, formatTokens, formatLatency, formatPct } from '../../lib/formatters';
import { CostTrendChart } from '../../lib/charts/CostTrendChart';
import { CostPieChart } from '../../lib/charts/CostPieChart';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useRunList } from '@/modules/runs/hooks';

export function CostOverviewPage() {
  const { t } = useTranslation(['common', 'costAnalysis']);
  const navigate = useNavigate();
  const overviewQuery = useCostOverview(30);
  const breakdownQuery = useBreakdownByModel(30);
  const trendQuery = useCostTrend('day', 30);
  const { data: runsData } = useRunList();

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
          {overviewQuery.error?.message ?? t('costAnalysis:overview.error')}
        </InlineMessage>
      </div>
    );
  }

  const overview = overviewQuery.data!;
  const breakdown = breakdownQuery.data;
  const trend = trendQuery.data;

  const metrics = [
    { label: t('costAnalysis:overview.totalSpend'), value: formatCost(overview.totalSpend), hint: formatPct(overview.spendChangePct), accent: 'blue' as const },
    { label: t('costAnalysis:overview.totalRequests'), value: String(overview.totalRequests), hint: `前 ${formatCost(overview.prevTotalSpend)}`, accent: 'violet' as const },
    { label: t('costAnalysis:overview.totalTokens'), value: formatTokens(overview.totalTokens), accent: 'teal' as const },
    { label: t('costAnalysis:overview.avgLatency'), value: formatLatency(overview.avgLatencyMs), accent: 'amber' as const },
  ];

  return (
    <div className="flex flex-col gap-6 p-6">
      <MetricStrip items={metrics} columns={4} />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {/* 成本趋势 */}
        <div className="border border-border rounded-[2px] bg-surface px-6 py-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
            {t('costAnalysis:overview.costTrend')}
          </h3>
          {trend && <CostTrendChart data={trend} />}
        </div>

        {/* 模型分布 */}
        <div className="border border-border rounded-[2px] bg-surface px-6 py-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
            {t('costAnalysis:overview.modelDistribution')}
          </h3>
          {breakdown && <CostPieChart data={breakdown.slice(0, 6)} />}
        </div>
      </div>

      {/* Top 模型列表 */}
      {overview.topModels.length > 0 && (
        <div className="border border-border rounded-[2px] bg-surface px-6 py-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
            {t('costAnalysis:overview.topModels')}
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

      {/* 最近运行成本 */}
      {runsData && runsData.items.length > 0 && (
        <div className="border border-border rounded-[2px] bg-surface px-6 py-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
              {t('costAnalysis:overview.recentRunsCost')}
            </h3>
            <button
              type="button"
              onClick={() => navigate('/runs')}
              className="text-xs font-medium text-primary hover:underline"
            >
              {t('costAnalysis:overview.viewAllRuns')}
            </button>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-text-muted">
                <th className="pb-2 font-medium">Run ID</th>
                <th className="pb-2 font-medium">Agent</th>
                <th className="pb-2 font-medium text-right">耗时</th>
                <th className="pb-2 font-medium text-right">花费</th>
                <th className="pb-2 font-medium text-right">状态</th>
              </tr>
            </thead>
            <tbody>
              {runsData.items.slice(0, 5).map((run) => (
                <tr
                  key={run.id}
                  className="cursor-pointer border-b border-border-subtle last:border-0 hover:bg-surface-raised"
                  onClick={() => navigate(`/runs/${run.id}`)}
                >
                  <td className="py-2 font-mono text-xs text-primary">#{run.id.slice(0, 8)}</td>
                  <td className="py-2 text-text">{run.agentKey}</td>
                  <td className="py-2 text-right text-text-secondary">
                    {run.durationMs != null ? `${(run.durationMs / 1000).toFixed(2)}s` : '—'}
                  </td>
                  <td className="py-2 text-right font-medium text-text">
                    {run.costUsd != null ? formatCost(run.costUsd) : '—'}
                  </td>
                  <td className="py-2 text-right">
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                      run.status === 'success' ? 'bg-success/10 text-success' :
                      run.status === 'failed' ? 'bg-error/10 text-error' :
                      run.status === 'running' ? 'bg-primary/10 text-primary' :
                      'bg-text-muted/10 text-text-muted'
                    }`}>
                      {run.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
