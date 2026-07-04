import { DonutSegment } from '@/shared/ui/charts';
import type { CostBreakdownItem } from '../../lib/contracts';
import { formatCost } from '../../lib/formatters';

const COLORS = [
  'rgb(59 130 246)',   // blue
  'rgb(139 92 246)',   // violet
  'rgb(20 184 166)',   // teal
  'rgb(245 158 11)',   // amber
  'rgb(239 68 68)',    // red
  'rgb(34 197 94)',    // green
  'rgb(236 72 153)',   // pink
  'rgb(168 85 247)',   // purple
];

const DEFAULT_SIZE = 160;
const SVG_PADDING = 2;
const DONUT_INNER_RADIUS_RATIO = 0.55;

export function CostPieChart({ data, size = DEFAULT_SIZE }: { data: CostBreakdownItem[]; size?: number }) {
  if (!data.length) {
    return <div className="flex h-[160px] items-center justify-center text-sm text-text-muted">暂无数据</div>;
  }

  const total = data.reduce((s, d) => s + d.totalEstimatedCost, 0) || 1;
  const cx = size / 2;
  const cy = size / 2;
  const outerR = size / 2 - SVG_PADDING;
  const innerR = outerR * DONUT_INNER_RADIUS_RATIO;

  let angle = -Math.PI / 2; // start from top
  const segments = data.map((item, i) => {
    const sweep = (item.totalEstimatedCost / total) * Math.PI * 2;
    const start = angle;
    const end = angle + sweep;
    angle = end;
    return { item, color: COLORS[i % COLORS.length], startAngle: start, endAngle: end };
  });

  return (
    <div className="flex items-center gap-4">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {segments.map((seg) => (
          <DonutSegment
            key={seg.item.scope}
            cx={cx}
            cy={cy}
            r={outerR}
            innerR={innerR}
            startAngle={seg.startAngle}
            endAngle={seg.endAngle}
            fill={seg.color}
          />
        ))}
        {/* center label */}
        <text x={cx} y={cy - 6} textAnchor="middle" dominantBaseline="middle" className="fill-text text-lg font-semibold">
          {formatCost(total)}
        </text>
        <text x={cx} y={cy + 10} textAnchor="middle" dominantBaseline="middle" className="fill-text-muted text-[10px]">
          总花费
        </text>
      </svg>
      {/* legend */}
      <div className="flex flex-col gap-1 text-xs">
        {segments.map((seg) => (
          <div key={seg.item.scope} className="flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: seg.color }} />
            <span className="text-text-secondary">{seg.item.scope}</span>
            <span className="ml-auto font-medium text-text">{formatCost(seg.item.totalEstimatedCost)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
