import { SvgChart, AreaPath } from '@/shared/ui/charts';
import type { CostTrendPoint } from '../../lib/contracts';
import { formatCost } from '../../lib/formatters';

const Y_PADDING_FACTOR = 1.15;
const MAX_X_TICKS = 15;
const Y_TICK_COUNT = 5;
const DEFAULT_HEIGHT = 180;

/** 安全解析 period 字段为 MM-DD 格式（兼容各种日期格式） */
function formatPeriodLabel(period: string): string {
  const d = new Date(period);
  if (isNaN(d.getTime())) return period;
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${mm}-${dd}`;
}

export function CostTrendChart({ data, height = DEFAULT_HEIGHT }: { data: CostTrendPoint[]; height?: number }) {
  if (data.length < 2) {
    return <div className="flex h-[180px] items-center justify-center text-sm text-text-muted">数据不足，至少需要两个时间点</div>;
  }

  const costs = data.map((d) => d.totalCost);
  const maxCost = Math.max(...costs) * Y_PADDING_FACTOR || 1;

  const points = data.map((d, i) => [i, d.totalCost] as [number, number]);

  const xTicks = data.map((d, i) => ({
    value: i,
    label: formatPeriodLabel(d.period),
  }));

  const yMax = Math.ceil(maxCost);
  const yTicks = Array.from({ length: Y_TICK_COUNT }, (_, i) => {
    const v = (yMax * i) / (Y_TICK_COUNT - 1);
    return { value: v, label: formatCost(v) };
  });

  return (
    <SvgChart
      height={height}
      xDomain={[-0.5, data.length - 0.5]}
      yDomain={[0, yMax]}
      xTicks={xTicks.filter((_, i) => data.length <= MAX_X_TICKS || i % Math.ceil(data.length / MAX_X_TICKS) === 0)}
      yTicks={yTicks}
      padding={{ top: 8, right: 16, bottom: 28, left: 56 }}
    >
      {({ xScale, yScale }) => (
        <AreaPath
          points={points}
          xScale={xScale}
          yScale={yScale}
          baseY={0}
          fill="rgb(var(--color-primary) / 0.12)"
          stroke="rgb(var(--color-primary))"
          strokeWidth={1.5}
        />
      )}
    </SvgChart>
  );
}
