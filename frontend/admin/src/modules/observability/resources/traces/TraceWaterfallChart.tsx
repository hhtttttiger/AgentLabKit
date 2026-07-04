import type { SpanData } from '../../lib/contracts';
import { formatDuration, getSpanKindColor } from '../../lib/formatters';

/** SVG Waterfall 图 — 每行一个 span，按时间偏移排列。 */
export function TraceWaterfallChart({ spans, traceStart, emptyText = 'No span data' }: { spans: SpanData[]; traceStart: string; emptyText?: string }) {
  if (!spans.length) {
    return <div className="py-8 text-center text-sm text-text-muted">{emptyText}</div>;
  }

  const traceStartMs = new Date(traceStart).getTime();
  const startMs = Number.isNaN(traceStartMs) ? 0 : traceStartMs;

  // Compute time offsets
  const rows = spans.map((span) => {
    const spanStart = span.startedAtUtc ? new Date(span.startedAtUtc).getTime() : startMs;
    const spanEnd = span.completedAtUtc ? new Date(span.completedAtUtc).getTime() : spanStart;
    const validSpanStart = Number.isNaN(spanStart) ? startMs : spanStart;
    const validSpanEnd = Number.isNaN(spanEnd) ? validSpanStart : spanEnd;
    const offsetMs = Math.max(validSpanStart - startMs, 0);
    const durationMs = span.durationMs ?? Math.max(validSpanEnd - validSpanStart, 0);
    return { span, offsetMs, durationMs: Math.max(durationMs, 0) };
  });

  const maxOffset = Math.max(...rows.map((r) => r.offsetMs + r.durationMs), 1);
  const chartWidth = 600;
  const rowHeight = 28;
  const labelWidth = 200;
  const totalHeight = rows.length * rowHeight + 4;

  const xScale = (ms: number) => labelWidth + (ms / maxOffset) * (chartWidth - labelWidth);

  return (
    <svg width={chartWidth} height={totalHeight} viewBox={`0 0 ${chartWidth} ${totalHeight}`} className="select-none overflow-visible">
      {/* Header line */}
      <line x1={labelWidth} y1={0} x2={labelWidth} y2={totalHeight} className="stroke-border-subtle" strokeWidth={0.5} />

      {rows.map((row, i) => {
        const x1 = xScale(row.offsetMs);
        const x2 = xScale(row.offsetMs + row.durationMs);
        const barWidth = Math.max(x2 - x1, 2);
        const color = getSpanKindColor(row.span.spanKind);
        const y = i * rowHeight + 4;

        return (
          <g key={row.span.spanId}>
            {/* Label */}
            <text
              x={labelWidth - 8}
              y={y + rowHeight / 2 + 1}
              textAnchor="end"
              dominantBaseline="middle"
              className="fill-text-secondary text-[11px]"
            >
              {row.span.name}
            </text>

            {/* Bar */}
            <rect
              x={x1}
              y={y + 4}
              width={barWidth}
              height={rowHeight - 8}
              rx={2}
              fill={`rgb(${color} / 0.7)`}
              className="cursor-pointer transition-opacity hover:opacity-80"
            />

            {/* Duration label inside bar (if wide enough) */}
            {barWidth > 60 && (
              <text
                x={x1 + barWidth / 2}
                y={y + rowHeight / 2 + 1}
                textAnchor="middle"
                dominantBaseline="middle"
                className="fill-background text-[10px] font-medium"
              >
                {formatDuration(row.durationMs)}
              </text>
            )}

            {/* Duration label outside bar (if narrow) */}
            {barWidth <= 60 && row.durationMs > 0 && (
              <text
                x={x2 + 4}
                y={y + rowHeight / 2 + 1}
                dominantBaseline="middle"
                className="fill-text-muted text-[10px]"
              >
                {formatDuration(row.durationMs)}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
