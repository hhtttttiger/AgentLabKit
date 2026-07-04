/* ------------------------------------------------------------------ */
/*  SVG bar — horizontal or vertical                                  */
/* ------------------------------------------------------------------ */

export interface BarProps {
  x: number;
  y: number;
  width: number;
  height: number;
  fill?: string;
  /** border radius applied to the "tip" end */
  radius?: number;
  /** optional text label rendered inside the bar */
  label?: string;
  labelColor?: string;
  className?: string;
}

export function Bar({
  x,
  y,
  width,
  height,
  fill = 'rgb(var(--color-primary) / 0.7)',
  radius = 2,
  label,
  labelColor = 'rgb(var(--color-background-default))',
  className,
}: BarProps) {
  return (
    <g className={className}>
      <rect x={x} y={y} width={width} height={height} rx={radius} ry={radius} fill={fill} />
      {label && (
        <text
          x={x + width / 2}
          y={y + height / 2}
          textAnchor="middle"
          dominantBaseline="middle"
          fill={labelColor}
          fontSize={Math.min(height * 0.6, 11)}
        >
          {label}
        </text>
      )}
    </g>
  );
}
