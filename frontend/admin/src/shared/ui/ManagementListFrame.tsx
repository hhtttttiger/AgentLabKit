import type { PropsWithChildren, ReactNode } from 'react';
import { cn } from '@/shared/lib/cn';

function RefreshBar({ visible }: { visible: boolean }) {
  return (
    <div
      aria-hidden
      className={cn(
        'h-0.5 w-full overflow-hidden rounded-full transition-opacity duration-500',
        visible ? 'opacity-100' : 'opacity-0',
      )}
      style={{ background: 'rgb(var(--color-primary) / 0.12)' }}
    >
      <div
        className="refresh-bar-comet h-full w-1/4 rounded-full"
        style={{ background: 'linear-gradient(90deg, transparent, rgb(var(--color-primary)), transparent)' }}
      />
    </div>
  );
}

export function ManagementListFrame({
  toolbar,
  error,
  pagination,
  refreshing = false,
  children,
  className,
}: PropsWithChildren<{
  toolbar?: ReactNode;
  error?: ReactNode;
  pagination?: ReactNode;
  /** Pass `listQuery.isFetching` to show a progress bar while data is refetching. */
  refreshing?: boolean;
  className?: string;
}>) {
  return (
    <div className={cn('flex min-h-0 flex-1 flex-col gap-3', className)}>
      {toolbar}
      <RefreshBar visible={refreshing} />
      {error}
      <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
      {pagination}
    </div>
  );
}
