/**
 * MetricsCard — A reusable card for displaying a single metric.
 *
 * Used for dashboard summaries, KPIs, and overview stats.
 */

import type { ReactNode } from 'react';
import { cn } from '@/shared/lib/cn';

interface MetricsCardProps {
  label: string;
  value: string | number;
  hint?: string;
  icon?: ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  className?: string;
  onClick?: () => void;
}

export function MetricsCard({
  label,
  value,
  hint,
  icon,
  trend,
  trendValue,
  className,
  onClick,
}: MetricsCardProps) {
  const Component = onClick ? 'button' : 'div';

  return (
    <Component
      onClick={onClick}
      className={cn(
        'flex flex-col items-start gap-2 rounded-lg border border-border bg-surface p-4',
        onClick && 'cursor-pointer transition hover:bg-surface-raised',
        className,
      )}
    >
      <div className="flex w-full items-center justify-between">
        <span className="text-xs font-medium text-text-muted">{label}</span>
        {icon && <span className="text-text-muted">{icon}</span>}
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-bold text-text">{value}</span>
        {trend && trendValue && (
          <span
            className={cn(
              'text-xs font-medium',
              trend === 'up' && 'text-success',
              trend === 'down' && 'text-error',
              trend === 'neutral' && 'text-text-muted',
            )}
          >
            {trendValue}
          </span>
        )}
      </div>
      {hint && <span className="text-xs text-text-muted">{hint}</span>}
    </Component>
  );
}
