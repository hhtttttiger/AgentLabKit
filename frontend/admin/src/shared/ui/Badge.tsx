import type { PropsWithChildren } from 'react';
import { cn } from '@/shared/lib/cn';

export function Badge({
  children,
  tone = 'neutral',
}: PropsWithChildren<{ tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'info' }>) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-[2px] border px-2.5 py-1 text-xs font-semibold',
        tone === 'neutral' && 'border-border bg-background-subtle text-text-secondary',
        tone === 'success' && 'border-success/20 bg-success-subtle text-success-text',
        tone === 'warning' && 'border-warning/20 bg-warning-subtle text-warning-text',
        tone === 'danger' && 'border-error/20 bg-error-subtle text-error-text',
        tone === 'info' && 'border-primary/20 bg-primary-subtle text-primary',
      )}
    >
      {children}
    </span>
  );
}
