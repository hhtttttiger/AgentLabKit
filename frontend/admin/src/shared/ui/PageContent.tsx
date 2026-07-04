import type { PropsWithChildren } from 'react';
import { cn } from '@/shared/lib/cn';

export function PageContent({
  children,
  className,
  scroll = true,
}: PropsWithChildren<{
  className?: string;
  scroll?: boolean;
}>) {
  return (
    <div className={cn('min-h-0 flex-1 px-8 pt-5 pb-3', scroll ? 'overflow-y-auto' : 'flex flex-col', className)}>
      {children}
    </div>
  );
}
