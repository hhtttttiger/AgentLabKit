import { cn } from '@/shared/lib/cn';

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-[2px] bg-border/50', className)} />;
}

export function SkeletonRows({ columns = 4, rows = 5 }: { columns?: number; rows?: number }) {
  return (
    <div className="overflow-hidden rounded-[2px] border border-border bg-surface">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-border">
          <thead className="bg-background-subtle">
            <tr>
              {Array.from({ length: columns }, (_, i) => (
                <th key={i} className="px-4 py-3">
                  <Skeleton className="h-3 w-16" />
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {Array.from({ length: rows }, (_, rowIndex) => (
              <tr key={rowIndex}>
                {Array.from({ length: columns }, (_, colIndex) => (
                  <td key={colIndex} className="px-4 py-4">
                    <Skeleton className={`h-4 ${colIndex === 0 ? 'w-32' : 'w-20'}`} />
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

export function SkeletonCards({ count = 6 }: { count?: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="flex flex-col rounded-[2px] border border-border bg-surface p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 space-y-2">
              <Skeleton className="h-5 w-36" />
              <Skeleton className="h-3 w-24" />
            </div>
            <Skeleton className="h-6 w-12 rounded-[2px]" />
          </div>
          <Skeleton className="mt-3 h-4 w-full" />
          <Skeleton className="mt-1.5 h-4 w-3/4" />
          <div className="mt-4 flex gap-3">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-3 w-16" />
          </div>
          <div className="mt-3 flex gap-2">
            <Skeleton className="h-5 w-14 rounded-[2px]" />
            <Skeleton className="h-5 w-14 rounded-[2px]" />
          </div>
          <div className="mt-auto flex items-center justify-between border-t border-border-subtle pt-4 mt-4">
            <Skeleton className="h-3 w-24" />
            <div className="flex gap-2">
              <Skeleton className="h-control-sm w-14 rounded-[2px]" />
              <Skeleton className="h-control-sm w-14 rounded-[2px]" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
