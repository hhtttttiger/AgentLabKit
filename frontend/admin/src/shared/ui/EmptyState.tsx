import type { ReactNode } from 'react';

export function EmptyState({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="rounded-[2px] border border-dashed border-border-strong bg-surface px-6 py-12 text-center">
      <h3 className="text-lg font-semibold text-text">{title}</h3>
      {description ? <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-text-secondary">{description}</p> : null}
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}
