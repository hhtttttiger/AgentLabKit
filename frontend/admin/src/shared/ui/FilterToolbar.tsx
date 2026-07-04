import type { PropsWithChildren, ReactNode } from 'react';
import { cn } from '@/shared/lib/cn';

const FIELD_COMPACT =
  '[&_input]:h-control-sm [&_input]:rounded-[2px] [&_input]:px-3 [&_input]:py-1.5 [&_input]:text-xs [&_input]:placeholder:text-xs ' +
  '[&_select]:h-control-sm [&_select]:rounded-[2px] [&_select]:px-3 [&_select]:py-1.5 [&_select]:text-xs ' +
  '[&_button]:h-control-sm [&_button]:rounded-[2px] [&_button]:px-3 [&_button]:py-1.5 [&_button]:text-[11px] ' +
  '[&_label_span]:text-xs';

export function FilterToolbar({
  title,
  description,
  children,
  actions,
  compact = false,
}: PropsWithChildren<{ title?: string; description?: string; actions?: ReactNode; compact?: boolean }>) {
  const hasLead = Boolean(title || description);
  const hasHeader = hasLead || Boolean(actions);

  if (compact) {
    return (
      <div className={cn('animate-box-enter px-0 py-2', FIELD_COMPACT)}>
        {hasLead ? (
          <div className="mb-2">
            {title ? <div className="text-sm font-semibold text-text">{title}</div> : null}
            {description ? <div className="mt-1 text-sm leading-6 text-text-secondary">{description}</div> : null}
          </div>
        ) : null}
        <div className="flex items-end gap-2">
          <div className="flex flex-1 flex-wrap items-end gap-3 [&>*]:min-w-[140px] [&>*]:max-w-[240px] [&>*]:flex-1 [&>.filter-narrow]:max-w-[160px] [&>.filter-narrow]:flex-[0.5]">{children}</div>
          {actions ? <div className="shrink-0">{actions}</div> : null}
        </div>
      </div>
    );
  }

  return (
    <div className={cn('animate-box-enter rounded-[2px] border border-border bg-surface p-4', FIELD_COMPACT)}>
      {hasHeader ? (
        <div className="flex flex-wrap items-start justify-between gap-4">
          {hasLead ? (
            <div>
              {title ? <div className="text-sm font-semibold text-text">{title}</div> : null}
              {description ? <div className="mt-1 text-sm leading-6 text-text-secondary">{description}</div> : null}
            </div>
          ) : null}
          {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
        </div>
      ) : null}
      <div className={cn('grid gap-3 md:grid-cols-2 xl:grid-cols-4', hasHeader && 'mt-4')}>
        {children}
      </div>
    </div>
  );
}
