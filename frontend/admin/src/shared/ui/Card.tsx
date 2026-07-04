import type { PropsWithChildren, ReactNode } from 'react';
import { cn } from '@/shared/lib/cn';

export function Card({
  children,
  className,
  bodyClassName,
  title,
  description,
  actions,
}: PropsWithChildren<{ className?: string; bodyClassName?: string; title?: string; description?: string; actions?: ReactNode }>) {
  return (
    <section className={cn('rounded-[2px] border border-border bg-surface', className)}>
      {(title || actions) && (
        <div className="flex items-start justify-between gap-4 border-b border-border-subtle px-5 py-4">
          <div>
            {title ? <h2 className="text-base font-semibold text-text">{title}</h2> : null}
            {description ? <p className="mt-1 text-sm leading-6 text-text-secondary">{description}</p> : null}
          </div>
          {actions}
        </div>
      )}
      <div className={cn('p-5', bodyClassName)}>{children}</div>
    </section>
  );
}
