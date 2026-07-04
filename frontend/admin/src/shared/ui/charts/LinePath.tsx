/* ------------------------------------------------------------------ */
/*  SVG line chart path                                                */
/* ------------------------------------------------------------------ */

export interface LinePathProps {
  /** data points as [x, y] pairs in *data* coordinates */
  points: [number, number][];
  xScale: (v: number) => number;
  yScale: (v: number) => number;
  stroke?: string;
  strokeWidth?: number;
  /** render a dot at each data point */
  showDots?: boolean;
  dotRadius?: number;
}

export function LinePath({
  points,
  xScale,
  yScale,
  stroke = 'rgb(var(--color-primary))',
  strokeWidth = 1.5,
  showDots = false,
  dotRadius = 2.5,
}: LinePathProps) {
  if (points.length < 2) return null;

  const d = points
    .map(([x, y], i) => {
      const px = xScale(x);
      const py = yScale(y);
      return `${i === 0 ? 'M' : 'L'}${px},${py}`;
    })
    .join(' ');

  return (
    <>
      <path d={d} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinejoin="round" />
      {showDots &&
        points.map(([x, y], i) => (
          <circle key={i} cx={xScale(x)} cy={yScale(y)} r={dotRadius} fill={stroke} />
        ))}
    </>
  );
}
