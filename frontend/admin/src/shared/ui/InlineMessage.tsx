import type { ReactNode } from 'react';
import { cn } from '@/shared/lib/cn';

export function InlineMessage({
  children,
  tone = 'info',
}: {
  children: ReactNode;
  tone?: 'info' | 'error';
}) {
  return (
    <div
      className={cn(
        'rounded-[2px] border px-4 py-3 text-sm',
        tone === 'info' && 'border-border bg-surface text-text-secondary',
        tone === 'error' && 'border-error/20 bg-error-subtle text-error-text',
      )}
    >
      {children}
    </div>
  );
}
