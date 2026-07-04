import type { CSSProperties, ReactNode } from 'react';
import { cn } from '@/shared/lib/cn';

export function MetricStrip({
  items,
  columns = 4,
  compact = false,
  showHints = true,
}: {
  items: Array<{ label: string; value: ReactNode; hint?: string; accent?: 'blue' | 'violet' | 'teal' | 'amber' }>;
  columns?: 2 | 3 | 4;
  compact?: boolean;
  showHints?: boolean;
}) {
  return (
    <div
      className={cn(
        'grid gap-3',
        columns === 2 && 'md:grid-cols-2',
        columns === 3 && 'md:grid-cols-3',
        columns === 4 && 'md:grid-cols-2 xl:grid-cols-4',
      )}
    >
      {items.map((item, index) => {
        const accentStyle: CSSProperties | undefined = { animationDelay: `${index * 55}ms` };

        return (
        <div
          key={item.label}
          style={accentStyle}
          className={cn(
            'animate-box-enter border border-border bg-surface',
            compact
              ? 'rounded-[2px] px-4 py-3'
              : 'rounded-[2px] px-6 py-5',
          )}
        >
          <div className={cn('font-semibold uppercase tracking-[0.14em] text-text-muted', compact ? 'text-[11px]' : 'text-xs')}>
            {item.label}
          </div>
          <div className={cn('font-semibold tracking-[-0.03em] text-text', compact ? 'mt-1 text-[1.85rem] leading-none' : 'mt-2 text-[2rem] leading-none')}>
            {item.value}
          </div>
          {showHints && item.hint ? (
            <div className={cn('text-text-secondary', compact ? 'mt-1 text-xs leading-5' : 'mt-2 text-sm leading-5')}>{item.hint}</div>
          ) : null}
        </div>
        );
      })}
    </div>
  );
}
