import {
  formatAdminCompactNumber,
  formatAdminDateTime,
  formatAdminNumber,
  formatAdminPercent,
} from '@/shared/i18n/formatters';

export function formatCompact(value: number) {
  return formatAdminCompactNumber(value, { maximumFractionDigits: 1 });
}

export function formatNumber(value: number) {
  return formatAdminNumber(value, { maximumFractionDigits: 0 });
}

export function formatPercent(value: number) {
  return formatAdminPercent(value, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

export function formatLatency(ms: number) {
  if (ms < 1000) return `${formatAdminNumber(ms, { maximumFractionDigits: 0 })} ms`;
  return `${formatAdminNumber(ms / 1000, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} s`;
}

export function formatDateTime(iso: string | null) {
  return formatAdminDateTime(iso, {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function formatDateRange(start: string, end: string) {
  return `${formatDateTime(start)} – ${formatDateTime(end)}`;
}
