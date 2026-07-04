/* ------------------------------------------------------------------ */
/*  SVG area chart path — filled polygon under a line                 */
/* ------------------------------------------------------------------ */

export interface AreaPathProps {
  /** data points as [x, y] pairs in *data* coordinates */
  points: [number, number][];
  xScale: (v: number) => number;
  yScale: (v: number) => number;
  /** CSS color / tailwind class for the fill */
  fill?: string;
  /** fill opacity 0..1 */
  fillOpacity?: number;
  /** CSS color for the stroke */
  stroke?: string;
  strokeWidth?: number;
  /** y value used as the bottom of the area (defaults to yDomain min → 0 in pixel) */
  baseY?: number;
}

export function AreaPath({
  points,
  xScale,
  yScale,
  fill = 'rgb(var(--color-primary) / 0.15)',
  fillOpacity,
  stroke = 'rgb(var(--color-primary))',
  strokeWidth = 1.5,
  baseY = 0,
}: AreaPathProps) {
  if (points.length < 2) return null;

  const basePx = yScale(baseY);

  const lineD = points
    .map(([x, y], i) => {
      const px = xScale(x);
      const py = yScale(y);
      return `${i === 0 ? 'M' : 'L'}${px},${py}`;
    })
    .join(' ');

  /* close the polygon: last point → bottom-right → bottom-left */
  const areaD = `${lineD} L${xScale(points[points.length - 1][0])},${basePx} L${xScale(points[0][0])},${basePx} Z`;

  return (
    <>
      <path d={areaD} fill={fill} fillOpacity={fillOpacity} />
      <path d={lineD} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinejoin="round" />
    </>
  );
}
