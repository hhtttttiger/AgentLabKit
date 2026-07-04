import { useState, useRef, useEffect } from 'react';
import { BookOpen, MoreHorizontal, Pencil, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { formatAdminDate } from '@/shared/i18n/formatters';
import { useAdminLocale } from '@/shared/i18n/useAdminLocale';
import type { GlossaryCategoryView } from '../../../lib/contracts';

export function CategoryCard({
  category,
  onEdit,
  onDelete,
  onClick,
}: {
  category: GlossaryCategoryView;
  onEdit: () => void;
  onDelete: () => void;
  onClick: () => void;
}) {
  const { t } = useTranslation();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  useAdminLocale();

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
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[2px] bg-primary-subtle">
            <BookOpen size={20} className="text-primary" />
          </div>
          <div className="min-w-0">
            <h3 className="truncate text-base font-semibold text-text">{category.name}</h3>
            {category.description ? (
              <p className="mt-0.5 line-clamp-1 text-sm text-text-secondary">{category.description}</p>
            ) : null}
          </div>
        </div>

        <div ref={menuRef} className="relative">
          <button
            aria-label={t('modules.glossary.categoryCard.menuLabel')}
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
                {t('modules.glossary.categoryCard.actions.edit')}
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
                {t('modules.glossary.categoryCard.actions.delete')}
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between">
        <span className="text-xs text-text-muted">
          {formatAdminDate(category.createdAtUtc)}
        </span>
      </div>
    </div>
  );
}
