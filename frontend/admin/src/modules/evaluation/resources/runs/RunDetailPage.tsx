import { useParams, useNavigate } from 'react-router-dom';
import { useRunDetail } from '../configs/hooks';
import { MetricStrip } from '@/shared/ui/MetricStrip';
import { LinePath } from '@/shared/ui/charts';
import { SvgChart } from '@/shared/ui/charts';
import { useTranslation } from 'react-i18next';

export function RunDetailPage() {
  const { t } = useTranslation(['common', 'evaluation']);
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const { data: detail, isLoading } = useRunDetail(runId ?? '');

  if (isLoading || !detail) {
    return <div className="p-6 text-text-muted">{t('states.loading')}</div>;
  }

  const { run, results } = detail;
  const scores = results.map((r) => r.overallScore);
  const avgScore = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
  const passCount = results.filter((r) => r.overallScore >= 0.7).length;
  const errorCount = results.filter((r) => r.errorMessage).length;

  const metrics = [
    { label: '平均分', value: avgScore.toFixed(3), accent: 'blue' as const },
    { label: '用例总数', value: String(results.length), accent: 'violet' as const },
    { label: '通过数 (≥0.7)', value: String(passCount), accent: 'teal' as const },
    { label: '错误数', value: String(errorCount), accent: 'amber' as const },
  ];

  // Build score distribution chart data
  const scorePoints = results.map((r, i) => [i, r.overallScore] as [number, number]);

  return (
    <div className="flex flex-col gap-6 p-6">
      <button onClick={() => navigate('/evaluation/runs')} className="text-sm text-text-secondary hover:text-primary">← 返回运行列表</button>

      <div className="flex items-center gap-4">
        <h2 className="font-mono text-sm text-text-muted">Run #{run.id}</h2>
        <span className={`rounded-[2px] px-2 py-0.5 text-xs ${run.status === 'completed' ? 'bg-success/10 text-success' : run.status === 'running' ? 'bg-warning/10 text-warning' : 'bg-text-muted/10 text-text-muted'}`}>
          {run.status}
        </span>
      </div>

      <MetricStrip items={metrics} columns={4} compact />

      {/* Score trend chart */}
      {scorePoints.length >= 2 && (
        <div className="border border-border rounded-[2px] bg-surface px-6 py-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">分数分布</h3>
          <SvgChart
            height={160}
            xDomain={[-0.5, results.length - 0.5]}
            yDomain={[0, 1]}
            yTicks={[{ value: 0, label: '0' }, { value: 0.5, label: '0.5' }, { value: 1, label: '1.0' }]}
            padding={{ top: 8, right: 16, bottom: 24, left: 40 }}
          >
            {({ xScale, yScale }) => (
              <LinePath points={scorePoints} xScale={xScale} yScale={yScale} stroke="rgb(var(--color-primary))" showDots />
            )}
          </SvgChart>
        </div>
      )}

      {/* Results table */}
      <div className="rounded-[2px] border border-border bg-surface">
        <div className="px-6 py-3 text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
          用例结果 ({results.length})
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-text-muted">
              <th className="px-6 pb-2 font-medium">#</th>
              <th className="pb-2 font-medium">实际输出</th>
              <th className="pb-2 font-medium">总分</th>
              <th className="pb-2 font-medium">指标明细</th>
              <th className="pb-2 font-medium text-right">耗时</th>
            </tr>
          </thead>
          <tbody>
            {results.map((r, i) => (
              <tr key={r.id} className="border-b border-border-subtle last:border-0">
                <td className="px-6 py-2 text-text-secondary">{i + 1}</td>
                <td className="py-2 text-text">{r.actualOutput.slice(0, 80)}{r.actualOutput.length > 80 ? '…' : ''}</td>
                <td className="py-2">
                  <span className={`font-medium ${r.overallScore >= 0.7 ? 'text-success' : r.overallScore >= 0.4 ? 'text-warning' : 'text-error'}`}>
                    {r.overallScore.toFixed(3)}
                  </span>
                </td>
                <td className="py-2 text-xs text-text-secondary">
                  {r.metricResults.map((m) => (
                    <span key={m.metricName} className="mr-2">{m.metricName}: {m.score.toFixed(2)}</span>
                  ))}
                </td>
                <td className="py-2 text-right text-text-secondary">{r.durationMs}ms</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
