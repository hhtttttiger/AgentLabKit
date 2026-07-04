import { FileText, MoreHorizontal, Pencil, Trash2 } from 'lucide-react';
import { Badge } from '@/shared/ui/Badge';
import type { KbStatus, KbView } from '../../../lib/contracts';
import { useState, useRef, useEffect } from 'react';

const statusTone: Record<KbStatus, 'success' | 'warning' | 'neutral' | 'danger'> = {
  Active: 'success',
  Processing: 'warning',
  Disabled: 'neutral',
  Deleted: 'danger',
};

const statusLabel: Record<KbStatus, string> = {
  Active: '活跃',
  Processing: '处理中',
  Disabled: '已禁用',
  Deleted: '已删除',
};

export function KbCardView({
  kb,
  onEdit,
  onDelete,
  onClick,
}: {
  kb: KbView;
  onEdit: () => void;
  onDelete: () => void;
  onClick: () => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [menuOpen]);

  return (
    <div
      className="group relative flex cursor-pointer flex-col rounded-[2px] border border-border bg-surface p-5 transition hover:border-primary/30"
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[2px] bg-primary-subtle">
            <FileText size={20} className="text-primary" />
          </div>
          <div className="min-w-0">
            <h3 className="truncate text-base font-semibold text-text">{kb.name}</h3>
            {kb.description ? (
              <p className="mt-0.5 line-clamp-1 text-sm text-text-secondary">{kb.description}</p>
            ) : null}
          </div>
        </div>

        {/* Actions menu */}
        <div ref={menuRef} className="relative">
          <button
            className="rounded-lg p-1.5 text-text-muted hover:bg-state-hover hover:text-text"
            onClick={(e) => {
              e.stopPropagation();
              setMenuOpen(!menuOpen);
            }}
          >
            <MoreHorizontal size={16} />
          </button>
          {menuOpen && (
            <div className="absolute right-0 top-full z-10 mt-1 w-32 rounded-[2px] border border-border bg-surface py-1">
              <button
                className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-state-hover"
                onClick={(e) => {
                  e.stopPropagation();
                  setMenuOpen(false);
                  onEdit();
                }}
              >
                <Pencil size={14} />
                编辑
              </button>
              <button
                className="flex w-full items-center gap-2 px-3 py-2 text-sm text-error-text hover:bg-state-hover"
                onClick={(e) => {
                  e.stopPropagation();
                  setMenuOpen(false);
                  onDelete();
                }}
              >
                <Trash2 size={14} />
                删除
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="mt-4 flex items-center justify-between">
        <Badge tone={statusTone[kb.status]}>{statusLabel[kb.status]}</Badge>
        <span className="text-xs text-text-muted">{kb.documentCount} 个文档</span>
      </div>
    </div>
  );
}
