import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react';
import { createPortal } from 'react-dom';
import { CalendarDays, ChevronLeft, ChevronRight } from 'lucide-react';
import { useAdminLocale } from '@/shared/i18n/useAdminLocale';
import { cn } from '@/shared/lib/cn';
import { useTranslation } from 'react-i18next';

function FieldShell({
  id,
  label,
  labelSuffix,
  hint,
  error,
  compact = false,
  children,
}: {
  id: string;
  label: string;
  labelSuffix?: ReactNode;
  hint?: string;
  error?: string | null;
  compact?: boolean;
  children: ReactNode;
}) {
  return (
    <div className={cn('block', compact ? 'space-y-1.5' : 'space-y-2')}>
      {label ? (
        <label htmlFor={id} className="flex items-center gap-1">
          <span className={cn('font-medium text-text', compact ? 'text-[12px]' : 'text-sm')}>{label}</span>
          {labelSuffix}
        </label>
      ) : null}
      {children}
      {hint ? <span className="block text-sm leading-5 text-text-muted">{hint}</span> : null}
      {error ? <span className="block text-xs text-error-text">{error}</span> : null}
    </div>
  );
}

const baseControlClassName =
  'w-full min-h-control rounded-[2px] border border-border-strong bg-surface px-3.5 py-2.5 text-sm text-text outline-none transition placeholder:text-text-subtle focus:border-transparent focus:ring-2 focus:ring-state-focus/40 disabled:cursor-not-allowed disabled:bg-background-subtle disabled:text-text-subtle';
const compactControlClassName =
  'w-full h-control-sm rounded-[2px] border border-border bg-surface px-3 py-2 text-sm text-text outline-none transition placeholder:text-text-subtle focus:border-transparent focus:ring-2 focus:ring-state-focus/35 disabled:cursor-not-allowed disabled:bg-background-subtle disabled:text-text-subtle';

function parseIsoDate(value?: string | null) {
  if (!value) return null;
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;

  const [, year, month, day] = match;
  const date = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatIsoDate(value: Date) {
  const year = value.getUTCFullYear();
  const month = String(value.getUTCMonth() + 1).padStart(2, '0');
  const day = String(value.getUTCDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function startOfUtcMonth(value: Date) {
  return new Date(Date.UTC(value.getUTCFullYear(), value.getUTCMonth(), 1));
}

function addUtcMonths(value: Date, delta: number) {
  return new Date(Date.UTC(value.getUTCFullYear(), value.getUTCMonth() + delta, 1));
}

function isSameUtcDay(a: Date | null, b: Date | null) {
  if (!a || !b) return false;
  return a.getUTCFullYear() === b.getUTCFullYear()
    && a.getUTCMonth() === b.getUTCMonth()
    && a.getUTCDate() === b.getUTCDate();
}

function buildCalendarDays(month: Date) {
  const firstDay = startOfUtcMonth(month);
  const offset = firstDay.getUTCDay();
  const daysInMonth = new Date(Date.UTC(month.getUTCFullYear(), month.getUTCMonth() + 1, 0)).getUTCDate();
  const totalCells = Math.ceil((offset + daysInMonth) / 7) * 7;

  return Array.from({ length: totalCells }, (_, index) => {
    const dayNumber = index - offset + 1;
    if (dayNumber < 1 || dayNumber > daysInMonth) {
      return null;
    }

    return new Date(Date.UTC(month.getUTCFullYear(), month.getUTCMonth(), dayNumber));
  });
}

export function TextField({
  label,
  labelSuffix,
  hint,
  error,
  fieldSize = 'default',
  ...props
}: { label: string; labelSuffix?: ReactNode; hint?: string; error?: string | null; fieldSize?: 'default' | 'compact' } & InputHTMLAttributes<HTMLInputElement>) {
  const fieldId = useId();
  const { locale } = useAdminLocale();
  const isLocaleSensitiveDateInput = props.type === 'date' || props.type === 'datetime-local' || props.type === 'month' || props.type === 'time' || props.type === 'week';
  const inputLang = props.lang ?? (isLocaleSensitiveDateInput ? locale : undefined);
  return (
    <FieldShell id={props.id ?? fieldId} label={label} labelSuffix={labelSuffix} hint={hint} error={error} compact={fieldSize === 'compact'}>
      <input id={props.id ?? fieldId} lang={inputLang} className={cn(fieldSize === 'compact' ? compactControlClassName : baseControlClassName, error && 'border-error focus:border-transparent focus:ring-2 focus:ring-error/35')} {...props} />
    </FieldShell>
  );
}

export function DateField({
  label,
  hint,
  error,
  fieldSize = 'default',
  value,
  onChange,
  min,
  max,
  placeholder,
  disabled = false,
}: {
  label: string;
  hint?: string;
  error?: string | null;
  fieldSize?: 'default' | 'compact';
  value: string;
  onChange: (value: string) => void;
  min?: string;
  max?: string;
  placeholder?: string;
  disabled?: boolean;
}) {
  const fieldId = useId();
  const panelId = useId();
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLInputElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const { locale } = useAdminLocale();
  const { t } = useTranslation('common');
  const [open, setOpen] = useState(false);
  const [panelPosition, setPanelPosition] = useState({ top: 0, left: 0, width: 280 });
  const selectedDate = parseIsoDate(value);
  const selectedTime = selectedDate?.getTime();
  const minDate = parseIsoDate(min);
  const maxDate = parseIsoDate(max);
  const [visibleMonth, setVisibleMonth] = useState(() => startOfUtcMonth(selectedDate ?? new Date()));

  useEffect(() => {
    if (open) {
      setVisibleMonth(startOfUtcMonth(selectedDate ?? new Date()));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 故意按毫秒值比较，避免 selectedDate 对象引用变化导致重复触发
  }, [open, selectedTime]);

  const updatePanelPosition = useCallback(() => {
    const trigger = triggerRef.current;
    if (!trigger) {
      return;
    }

    const rect = trigger.getBoundingClientRect();
    setPanelPosition({
      top: rect.bottom + 8,
      left: rect.left,
      width: Math.max(rect.width, 280),
    });
  }, []);

  useEffect(() => {
    if (!open) return undefined;

    updatePanelPosition();

    const handleMouseDown = (event: MouseEvent) => {
      const target = event.target as Node;
      const clickedTrigger = containerRef.current?.contains(target) ?? false;
      const clickedPanel = panelRef.current?.contains(target) ?? false;
      if (!clickedTrigger && !clickedPanel) {
        setOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    };
    const handleViewportChange = () => {
      updatePanelPosition();
    };

    document.addEventListener('mousedown', handleMouseDown);
    document.addEventListener('keydown', handleKeyDown);
    window.addEventListener('resize', handleViewportChange);
    window.addEventListener('scroll', handleViewportChange, true);
    return () => {
      document.removeEventListener('mousedown', handleMouseDown);
      document.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('resize', handleViewportChange);
      window.removeEventListener('scroll', handleViewportChange, true);
    };
  }, [open, updatePanelPosition]);

  const displayValue = useMemo(() => {
    if (!selectedDate) return '';
    return new Intl.DateTimeFormat(locale, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      timeZone: 'UTC',
    }).format(selectedDate);
  }, [locale, selectedDate]);

  const monthLabel = useMemo(
    () => new Intl.DateTimeFormat(locale, { year: 'numeric', month: 'long', timeZone: 'UTC' }).format(visibleMonth),
    [locale, visibleMonth],
  );

  const weekdayLabels = useMemo(
    () => Array.from({ length: 7 }, (_, index) => new Intl.DateTimeFormat(locale, { weekday: 'short', timeZone: 'UTC' })
      .format(new Date(Date.UTC(2024, 0, 7 + index)))),
    [locale],
  );

  const fullDateFormatter = useMemo(
    () => new Intl.DateTimeFormat(locale, { dateStyle: 'full', timeZone: 'UTC' }),
    [locale],
  );

  const days = useMemo(() => buildCalendarDays(visibleMonth), [visibleMonth]);

  const isDisabledDate = (day: Date) => (
    (minDate !== null && day.getTime() < minDate.getTime())
    || (maxDate !== null && day.getTime() > maxDate.getTime())
  );

  return (
    <FieldShell id={fieldId} label={label} hint={hint} error={error} compact={fieldSize === 'compact'}>
      <div ref={containerRef} className="relative">
        <div className="relative">
          <input
            id={fieldId}
            ref={triggerRef}
            type="text"
            readOnly
            disabled={disabled}
            value={displayValue}
            placeholder={placeholder ?? t('datePicker.selectDate')}
            aria-haspopup="dialog"
            aria-expanded={open}
            aria-controls={open ? panelId : undefined}
            onClick={() => {
              if (!disabled) {
                if (!open) {
                  updatePanelPosition();
                }
                setOpen((current) => !current);
              }
            }}
            onKeyDown={(event) => {
              if (disabled) return;
              if (event.key === 'Enter' || event.key === ' ' || event.key === 'ArrowDown') {
                event.preventDefault();
                setOpen(true);
              }
            }}
            className={cn(
              fieldSize === 'compact' ? compactControlClassName : baseControlClassName,
              'cursor-pointer pr-10',
              error && 'border-error focus:border-transparent focus:ring-2 focus:ring-error/35',
            )}
          />
          <CalendarDays
            aria-hidden="true"
            className={cn(
              'pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-text-muted',
              fieldSize === 'compact' ? 'h-4 w-4' : 'h-5 w-5',
            )}
          />
        </div>

        {open ? createPortal(
          <div
            id={panelId}
            ref={panelRef}
            role="dialog"
            aria-label={monthLabel}
            className="fixed z-[120] rounded-[2px] border border-border bg-surface p-3"
            style={{
              top: `${panelPosition.top}px`,
              left: `${panelPosition.left}px`,
              width: `${panelPosition.width}px`,
            }}
          >
            <div className="mb-3 flex items-center justify-between gap-2">
              <button
                type="button"
                aria-label={t('datePicker.previousMonth')}
                className="inline-flex h-control-sm w-9 items-center justify-center rounded-[2px] text-text-secondary transition hover:bg-state-hover hover:text-text"
                onClick={() => setVisibleMonth((current) => addUtcMonths(current, -1))}
              >
                <ChevronLeft size={16} />
              </button>
              <div className="text-sm font-semibold text-text">{monthLabel}</div>
              <button
                type="button"
                aria-label={t('datePicker.nextMonth')}
                className="inline-flex h-control-sm w-9 items-center justify-center rounded-[2px] text-text-secondary transition hover:bg-state-hover hover:text-text"
                onClick={() => setVisibleMonth((current) => addUtcMonths(current, 1))}
              >
                <ChevronRight size={16} />
              </button>
            </div>

            <div className="mb-2 grid grid-cols-7 gap-1">
              {weekdayLabels.map((weekday) => (
                <div key={weekday} className="flex h-8 items-center justify-center text-xs font-medium text-text-muted">
                  {weekday}
                </div>
              ))}
            </div>

            <div className="grid grid-cols-7 gap-1">
              {days.map((day, index) => {
                if (!day) {
                  return <div key={`empty-${index}`} className="h-control-sm w-9" />;
                }

                const disabledDay = isDisabledDate(day);
                const selected = isSameUtcDay(day, selectedDate);

                return (
                  <button
                    key={formatIsoDate(day)}
                    type="button"
                    aria-label={fullDateFormatter.format(day)}
                    disabled={disabledDay}
                    onClick={() => {
                      onChange(formatIsoDate(day));
                      setOpen(false);
                    }}
                    className={cn(
                      'flex h-control-sm w-9 items-center justify-center rounded-[2px] text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-state-focus/30',
                      selected
                        ? 'bg-primary text-text-inverse'
                        : 'text-text hover:bg-background-subtle',
                      disabledDay && 'cursor-not-allowed text-text-subtle opacity-50 hover:bg-transparent',
                    )}
                  >
                    {day.getUTCDate()}
                  </button>
                );
              })}
            </div>

            {value ? (
              <div className="mt-3 flex justify-end">
                <button
                  type="button"
                  className="inline-flex min-h-control-sm items-center justify-center rounded-[2px] px-3 py-1.5 text-xs font-medium text-text-secondary transition hover:bg-state-hover hover:text-text"
                  onClick={() => {
                    onChange('');
                    setOpen(false);
                  }}
                >
                  {t('datePicker.clear')}
                </button>
              </div>
            ) : null}
          </div>,
          document.body,
        ) : null}
      </div>
    </FieldShell>
  );
}

export function NumberField({
  label,
  hint,
  error,
  fieldSize = 'default',
  ...props
}: { label: string; hint?: string; error?: string | null; fieldSize?: 'default' | 'compact' } & InputHTMLAttributes<HTMLInputElement>) {
  const fieldId = useId();
  return (
    <FieldShell id={props.id ?? fieldId} label={label} hint={hint} error={error} compact={fieldSize === 'compact'}>
      <input id={props.id ?? fieldId} type="number" className={cn(fieldSize === 'compact' ? compactControlClassName : baseControlClassName, error && 'border-error focus:border-transparent focus:ring-2 focus:ring-error/35')} {...props} />
    </FieldShell>
  );
}

export function SelectField({
  label,
  hint,
  error,
  fieldSize = 'default',
  children,
  ...props
}: { label: string; hint?: string; error?: string | null; fieldSize?: 'default' | 'compact' } & SelectHTMLAttributes<HTMLSelectElement>) {
  const fieldId = useId();
  return (
    <FieldShell id={props.id ?? fieldId} label={label} hint={hint} error={error} compact={fieldSize === 'compact'}>
      <select id={props.id ?? fieldId} className={cn(fieldSize === 'compact' ? compactControlClassName : baseControlClassName, error && 'border-error focus:border-transparent focus:ring-2 focus:ring-error/35')} {...props}>
        {children}
      </select>
    </FieldShell>
  );
}

export function TextAreaField({
  label,
  hint,
  error,
  className,
  ...props
}: { label: string; hint?: string; error?: string | null } & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const fieldId = useId();
  return (
    <FieldShell id={props.id ?? fieldId} label={label} hint={hint} error={error}>
      <textarea id={props.id ?? fieldId} className={cn(baseControlClassName, 'min-h-28 resize-y', error && 'border-error focus:border-transparent focus:ring-2 focus:ring-error/35', className)} {...props} />
    </FieldShell>
  );
}

export function ToggleField({
  label,
  hint,
  checked,
  onChange,
  disabled = false,
}: {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <label className={cn('flex items-center justify-between rounded-[2px] border border-border bg-surface px-4 py-3', disabled && 'opacity-70')}>
      <div>
        <div className="text-sm font-medium text-text">{label}</div>
        {hint ? <div className="mt-1 text-sm leading-5 text-text-muted">{hint}</div> : null}
      </div>
      <button
        type="button"
        aria-pressed={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={cn(
          'relative h-7 w-12 rounded-full transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-state-focus/30 disabled:cursor-not-allowed',
          checked ? 'bg-primary' : 'bg-border-strong',
        )}
      >
        <span
          className={cn(
            'absolute top-1 h-5 w-5 rounded-full bg-surface transition',
            checked ? 'left-6' : 'left-1',
          )}
        />
      </button>
    </label>
  );
}
