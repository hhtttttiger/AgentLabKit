/**
 * Shared date-range helpers for model-monitoring filters.
 *
 * Converts a local-date string ("2026-03-01") to a full-day ISO range
 * so the backend sees [start-of-day, end-of-day) in UTC.
 */

export function toStartOfDayIso(value: string): string | undefined {
  if (!value) return undefined;
  const parts = value.split('-').map(Number);
  return new Date(Date.UTC(parts[0], parts[1] - 1, parts[2])).toISOString();
}

export function toEndOfDayIso(value: string): string | undefined {
  if (!value) return undefined;
  const parts = value.split('-').map(Number);
  return new Date(Date.UTC(parts[0], parts[1] - 1, parts[2], 23, 59, 59, 999)).toISOString();
}
