import type { PropsWithChildren, ReactNode } from 'react';
import { PageContent } from './PageContent';

export function SectionPageFrame({
  sectionTitle,
  title,
  description,
  actions,
  supporting,
  children,
  contentClassName,
  scroll = true,
}: PropsWithChildren<{
  sectionTitle: string;
  title: string;
  description?: string;
  actions?: ReactNode;
  supporting?: ReactNode;
  contentClassName?: string;
  scroll?: boolean;
}>) {
  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border bg-surface/50 px-8 py-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-baseline gap-2 text-sm">
              <span className="text-text-muted">{sectionTitle}</span>
              <span className="text-text-muted/50">/</span>
              <h2 className="text-lg font-semibold text-text">{title}</h2>
            </div>
            {description ? <p className="mt-1 text-sm text-text-secondary">{description}</p> : null}
          </div>
          {actions ? <div className="flex shrink-0 flex-wrap gap-2">{actions}</div> : null}
        </div>
        {supporting ? <div className="mt-3">{supporting}</div> : null}
      </div>
      <PageContent className={contentClassName} scroll={scroll}>
        {children}
      </PageContent>
    </div>
  );
}
