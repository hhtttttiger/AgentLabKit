/* ------------------------------------------------------------------ */
/*  SVG donut / pie segment — arc path                                 */
/* ------------------------------------------------------------------ */

export interface DonutSegmentProps {
  /** center x */
  cx: number;
  /** center y */
  cy: number;
  /** outer radius */
  r: number;
  /** inner radius (0 = pie, >0 = donut) */
  innerR?: number;
  /** start angle in radians */
  startAngle: number;
  /** end angle in radians */
  endAngle: number;
  fill: string;
  /** stroke between segments */
  stroke?: string;
  strokeWidth?: number;
  className?: string;
}

function polarToCartesian(cx: number, cy: number, r: number, angle: number) {
  return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
}

export function DonutSegment({
  cx,
  cy,
  r,
  innerR = 0,
  startAngle,
  endAngle,
  fill,
  stroke = 'rgb(var(--color-background-default))',
  strokeWidth = 1,
  className,
}: DonutSegmentProps) {
  const outerStart = polarToCartesian(cx, cy, r, startAngle);
  const outerEnd = polarToCartesian(cx, cy, r, endAngle);
  const largeArc = endAngle - startAngle > Math.PI ? 1 : 0;

  if (innerR === 0) {
    /* simple pie slice */
    const d = [
      `M${cx},${cy}`,
      `L${outerStart.x},${outerStart.y}`,
      `A${r},${r} 0 ${largeArc} 1 ${outerEnd.x},${outerEnd.y}`,
      'Z',
    ].join(' ');
    return <path d={d} fill={fill} stroke={stroke} strokeWidth={strokeWidth} className={className} />;
  }

  /* donut arc */
  const innerStart = polarToCartesian(cx, cy, innerR, endAngle);
  const innerEnd = polarToCartesian(cx, cy, innerR, startAngle);

  const d = [
    `M${outerStart.x},${outerStart.y}`,
    `A${r},${r} 0 ${largeArc} 1 ${outerEnd.x},${outerEnd.y}`,
    `L${innerStart.x},${innerStart.y}`,
    `A${innerR},${innerR} 0 ${largeArc} 0 ${innerEnd.x},${innerEnd.y}`,
    'Z',
  ].join(' ');

  return <path d={d} fill={fill} stroke={stroke} strokeWidth={strokeWidth} className={className} />;
}
