import { ChevronRight, FolderOpen } from 'lucide-react';

export type BreadcrumbItem = {
  id: string | null;
  name: string;
};

type Props = {
  path: BreadcrumbItem[];
  onNavigate: (item: BreadcrumbItem) => void;
};

export function KbFolderBreadcrumb({ path, onNavigate }: Props) {
  if (path.length <= 1) return null;

  return (
    <div className="flex flex-wrap items-center gap-1 text-sm">
      <FolderOpen size={14} className="shrink-0 text-text-muted" />
      {path.map((item, index) => {
        const isLast = index === path.length - 1;

        return (
          <span key={item.id ?? 'root'} className="flex min-w-0 items-center gap-1">
            {index > 0 ? <ChevronRight size={13} className="shrink-0 text-text-muted" /> : null}
            {isLast ? (
              <span className="truncate font-medium text-text">{item.name}</span>
            ) : (
              <button
                type="button"
                className="truncate text-text-secondary transition hover:text-primary hover:underline"
                onClick={() => onNavigate(item)}
              >
                {item.name}
              </button>
            )}
          </span>
        );
      })}
    </div>
  );
}
