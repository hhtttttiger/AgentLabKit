import type { ReactNode } from 'react';

/** Compact field used in detail cards and tabs to display a labelled value.
 *  Shared across ModelCardDetailPage, ModelCardOverviewTab, and ModelCardInstancesTab. */
export function DetailField({
  label,
  value,
  tone = 'default',
}: {
  label: string;
  value: ReactNode;
  tone?: 'default' | 'strong';
}) {
  return (
    <div className="rounded-[2px] border border-border-subtle bg-background-subtle/70 px-4 py-3">
      <div className="text-[11px] uppercase tracking-[0.16em] text-text-muted">{label}</div>
      <div
        className={
          tone === 'strong'
            ? 'mt-2 text-base font-semibold text-text'
            : 'mt-2 text-sm font-medium text-text'
        }
      >
        {value}
      </div>
    </div>
  );
}

/** Large-stat card for numeric summaries (total, healthy%, etc.).
 *  Shared across ModelCardDetailPage and ModelCardInstancesTab. */
export function InstanceStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[2px] border border-border-subtle bg-background-subtle/70 px-4 py-3">
      <div className="text-xs text-text-muted">{label}</div>
      <div className="mt-1 text-lg font-semibold text-text">{value}</div>
    </div>
  );
}
