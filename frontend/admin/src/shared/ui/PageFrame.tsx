import type { PropsWithChildren, ReactNode } from 'react';
import { cn } from '@/shared/lib/cn';
import { PageContent } from './PageContent';

export function PageFrame({
  header,
  eyebrow,
  title,
  description,
  actions,
  supporting,
  children,
  contentClassName,
  headerClassName,
  headerBodyClassName,
  supportingClassName,
  scroll = true,
}: PropsWithChildren<{
  header?: ReactNode;
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
  supporting?: ReactNode;
  contentClassName?: string;
  headerClassName?: string;
  headerBodyClassName?: string;
  supportingClassName?: string;
  scroll?: boolean;
}>) {
  return (
    <div className="flex h-full flex-col">
      <div className={cn('border-b border-border bg-surface px-8 py-7', headerClassName)}>
        {header ? (
          header
        ) : (
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div className={cn('max-w-4xl', headerBodyClassName)}>
              {eyebrow ? <div className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">{eyebrow}</div> : null}
              <h2 className="mt-2 text-[2rem] font-semibold tracking-[-0.04em] text-text">{title}</h2>
              {description ? <p className="mt-3 text-base leading-7 text-text-secondary">{description}</p> : null}
              {supporting ? <div className={cn('mt-5', supportingClassName)}>{supporting}</div> : null}
            </div>
            {actions ? <div className="flex shrink-0 flex-wrap gap-2">{actions}</div> : null}
          </div>
        )}
      </div>
      <PageContent className={contentClassName} scroll={scroll}>
        {children}
      </PageContent>
    </div>
  );
}
