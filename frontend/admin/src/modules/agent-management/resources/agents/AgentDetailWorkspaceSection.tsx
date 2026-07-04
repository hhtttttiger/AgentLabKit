import type { PropsWithChildren, ReactNode } from 'react';

export function AgentDetailWorkspaceSection({
  title,
  description,
  actions,
  children,
}: PropsWithChildren<{
  title: string;
  description?: string;
  actions?: ReactNode;
}>) {
  return (
    <section
      data-testid="agent-detail-section"
      className="overflow-hidden rounded-[2px] border border-border bg-surface"
    >
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border px-6 py-5">
        <div className="max-w-3xl">
          <h3 className="text-lg font-semibold text-text">{title}</h3>
          {description ? <p className="mt-1 text-sm text-text-secondary">{description}</p> : null}
        </div>
        {actions ? <div className="flex shrink-0 flex-wrap gap-2">{actions}</div> : null}
      </div>
      <div className="px-6 py-5">{children}</div>
    </section>
  );
}
