import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useState, type KeyboardEvent, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

const PAGE_SIZE_OPTIONS = [10, 20, 50, 100];

export function Pagination({
  page,
  pageSize,
  totalCount,
  onChange,
  onPageSizeChange,
}: {
  page: number;
  pageSize: number;
  totalCount: number;
  onChange: (page: number) => void;
  /**
   * Called when the user selects a new page size.
   * **Callers must also reset `page` to `1`** when this fires, otherwise the
   * current page may be out of range for the new page size.
   */
  onPageSizeChange?: (pageSize: number) => void;
}) {
  const { t } = useTranslation('common');
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const [jumpValue, setJumpValue] = useState('');

  function handleJump(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key !== 'Enter') return;
    const n = parseInt(jumpValue, 10);
    if (!isNaN(n) && n >= 1 && n <= totalPages) onChange(n);
    setJumpValue('');
  }

  const navBtn = (disabled: boolean, onClick: () => void, label: string, children: ReactNode) => (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      aria-label={label}
      title={label}
      className="flex h-7 w-7 items-center justify-center rounded-lg text-text-secondary transition hover:bg-state-hover hover:text-text disabled:cursor-not-allowed disabled:opacity-35"
    >
      {children}
    </button>
  );

  return (
    <div className="flex items-center justify-between border-t border-border py-2 text-sm text-text-secondary">
      {/* left slot — batch actions can be injected here */}
      <div />

      <div className="flex items-center gap-4">
        <span>
          {t('pagination.totalPrefix')}
          <span className="font-medium text-text">{totalCount}</span>
          {t('pagination.totalSuffix')}
        </span>

        {onPageSizeChange && (
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            className="rounded-lg border border-border bg-surface px-2 py-1 text-xs text-text focus:outline-none focus:ring-2 focus:ring-primary/30"
          >
            {PAGE_SIZE_OPTIONS.map((n) => (
              <option key={n} value={n}>{t('pagination.pageSizeOption', { count: n })}</option>
            ))}
          </select>
        )}

        <div className="flex items-center gap-0.5">
          {navBtn(page <= 1, () => onChange(page - 1), t('pagination.previousPage'), <ChevronLeft size={14} />)}
          <span className="min-w-[4.5rem] px-2 text-center tabular-nums">
            <span className="font-medium text-text">{page}</span>
            <span className="mx-1 text-border">/</span>
            {totalPages}
          </span>
          {navBtn(page >= totalPages, () => onChange(page + 1), t('pagination.nextPage'), <ChevronRight size={14} />)}
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-text-muted">{t('pagination.jumpTo')}</span>
          <input
            type="number"
            min={1}
            max={totalPages}
            value={jumpValue}
            onChange={(e) => setJumpValue(e.target.value)}
            onKeyDown={handleJump}
            placeholder={String(page)}
            className="w-11 rounded-lg border border-border bg-surface px-1.5 py-1 text-center text-xs text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/30 [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
          />
          <span className="text-text-muted">{t('pagination.pageUnit')}</span>
        </div>
      </div>
    </div>
  );
}
