import { type ReactNode, useRef, useState, useEffect } from 'react';
import { cn } from '@/shared/lib/cn';

/* ------------------------------------------------------------------ */
/*  Responsive SVG container with padding, axes, and hover grid       */
/* ------------------------------------------------------------------ */

export interface AxisTick {
  value: number;
  label: string;
}

export interface SvgChartProps {
  /** viewBox width — defaults to container width via ResizeObserver */
  width?: number;
  /** viewBox height */
  height?: number;
  /** top / right / bottom / left padding in SVG units */
  padding?: { top?: number; right?: number; bottom?: number; left?: number };
  /** optional X-axis ticks */
  xTicks?: AxisTick[];
  /** optional Y-axis ticks */
  yTicks?: AxisTick[];
  /** format X tick label (defaults to .label) */
  xTickFormat?: (tick: AxisTick) => string;
  /** format Y tick label (defaults to .label) */
  yTickFormat?: (tick: AxisTick) => string;
  /** X-axis data domain [min, max] */
  xDomain: [number, number];
  /** Y-axis data domain [min, max] */
  yDomain: [number, number];
  /** chart content rendered between axes */
  children: (scales: { xScale: (v: number) => number; yScale: (v: number) => number; innerW: number; innerH: number }) => ReactNode;
  className?: string;
}

const defaultPadding = { top: 8, right: 8, bottom: 28, left: 48 };

export function SvgChart({
  height = 200,
  padding = defaultPadding,
  xTicks,
  yTicks,
  xTickFormat = (t) => t.label,
  yTickFormat = (t) => t.label,
  xDomain,
  yDomain,
  children,
  className,
}: SvgChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(400);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setWidth(Math.floor(entry.contentRect.width));
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const p = { ...defaultPadding, ...padding };
  const innerW = width - p.left - p.right;
  const innerH = height - p.top - p.bottom;

  const xScale = (v: number) =>
    p.left + ((v - xDomain[0]) / (xDomain[1] - xDomain[0])) * innerW;
  const yScale = (v: number) =>
    p.top + innerH - ((v - yDomain[0]) / (yDomain[1] - yDomain[0])) * innerH;

  return (
    <div ref={containerRef} className={cn('w-full', className)}>
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        className="select-none overflow-visible"
      >
        {/* grid lines */}
        {yTicks?.map((t) => (
          <line
            key={t.value}
            x1={p.left}
            x2={p.left + innerW}
            y1={yScale(t.value)}
            y2={yScale(t.value)}
            className="stroke-border-subtle"
            strokeWidth={0.5}
          />
        ))}

        {/* chart body */}
        {children({ xScale, yScale, innerW, innerH })}

        {/* X axis */}
        {xTicks?.map((t) => (
          <text
            key={t.value}
            x={xScale(t.value)}
            y={height - 4}
            textAnchor="middle"
            className="fill-text-muted text-[10px]"
          >
            {xTickFormat(t)}
          </text>
        ))}

        {/* Y axis */}
        {yTicks?.map((t) => (
          <text
            key={t.value}
            x={p.left - 6}
            y={yScale(t.value)}
            textAnchor="end"
            dominantBaseline="middle"
            className="fill-text-muted text-[10px]"
          >
            {yTickFormat(t)}
          </text>
        ))}
      </svg>
    </div>
  );
}
