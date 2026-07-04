import type { ReactNode } from 'react';
import { SkeletonRows } from './Skeleton';

export type TableColumn<T> = {
  key: string;
  header: ReactNode;
  render: (row: T) => ReactNode;
  className?: string;
  headerClassName?: string;
};

export function DataTable<T>({
  columns,
  rows,
  getRowKey,
  emptyState,
  loading = false,
}: {
  columns: TableColumn<T>[];
  rows: T[];
  getRowKey: (row: T) => string;
  emptyState: ReactNode;
  loading?: boolean;
}) {
  if (loading) {
    return <SkeletonRows columns={columns.length} />;
  }

  if (!rows.length) {
    return <>{emptyState}</>;
  }

  return (
    <div className="animate-box-enter overflow-hidden rounded-[2px] border border-border bg-surface">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-border">
          <thead className="bg-background-subtle text-left">
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  className={`px-4 py-2 text-xs font-semibold uppercase tracking-[0.12em] text-text-muted ${column.headerClassName ?? ''}`}
                >
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map((row) => (
              <tr key={getRowKey(row)} className="align-top transition hover:bg-state-hover/70">
                {columns.map((column) => (
                  <td key={column.key} className={`px-4 py-2.5 text-sm leading-6 text-text-secondary ${column.className ?? ''}`}>
                    {column.render(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
