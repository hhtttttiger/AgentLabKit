import i18n from './index';

type DateValue = string | number | Date | null | undefined;
type RelativeTimeOptions = Intl.RelativeTimeFormatOptions & {
  now?: DateValue;
  maxRelativeMs?: number;
  fallbackOptions?: Intl.DateTimeFormatOptions;
};

export function getAdminFormattingLocale() {
  return i18n.resolvedLanguage ?? i18n.language;
}

function resolveAdminFormattingLocale(locale?: string) {
  return locale ?? getAdminFormattingLocale();
}

function parseAdminDateValue(value: DateValue) {
  if (value === null || value === undefined || value === '') {
    return null;
  }

  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return date;
}

export function formatAdminDateTime(
  value: DateValue,
  options?: Intl.DateTimeFormatOptions,
  locale?: string,
) {
  const date = parseAdminDateValue(value);
  if (!date) {
    return '-';
  }

  const formattingLocale = resolveAdminFormattingLocale(locale);
  if (!options) {
    return date.toLocaleString(formattingLocale);
  }

  return new Intl.DateTimeFormat(formattingLocale, options).format(date);
}

export function formatAdminDate(
  value: DateValue,
  options?: Intl.DateTimeFormatOptions,
  locale?: string,
) {
  const date = parseAdminDateValue(value);
  if (!date) {
    return '-';
  }

  const formattingLocale = resolveAdminFormattingLocale(locale);
  if (!options) {
    return date.toLocaleDateString(formattingLocale);
  }

  return new Intl.DateTimeFormat(formattingLocale, options).format(date);
}

export function formatAdminTime(
  value: DateValue,
  options?: Intl.DateTimeFormatOptions,
  locale?: string,
) {
  const date = parseAdminDateValue(value);
  if (!date) {
    return '-';
  }

  const formattingLocale = resolveAdminFormattingLocale(locale);
  if (!options) {
    return date.toLocaleTimeString(formattingLocale);
  }

  return new Intl.DateTimeFormat(formattingLocale, options).format(date);
}

export function formatAdminRelativeTime(
  value: DateValue,
  options?: RelativeTimeOptions,
  locale?: string,
) {
  const date = parseAdminDateValue(value);
  if (!date) {
    return '-';
  }

  const {
    now,
    maxRelativeMs = 7 * 24 * 60 * 60 * 1000,
    fallbackOptions,
    ...relativeOptions
  } = options ?? {};
  const nowDate = parseAdminDateValue(now) ?? new Date();
  const diffMs = date.getTime() - nowDate.getTime();
  const absDiffMs = Math.abs(diffMs);

  if (absDiffMs >= maxRelativeMs) {
    return formatAdminDate(date, fallbackOptions, locale);
  }

  const formatter = new Intl.RelativeTimeFormat(resolveAdminFormattingLocale(locale), {
    numeric: 'auto',
    ...relativeOptions,
  });

  if (absDiffMs < 60_000) {
    return formatter.format(0, 'second');
  }

  if (absDiffMs < 3_600_000) {
    return formatter.format(Math.trunc(diffMs / 60_000), 'minute');
  }

  if (absDiffMs < 86_400_000) {
    return formatter.format(Math.trunc(diffMs / 3_600_000), 'hour');
  }

  return formatter.format(Math.trunc(diffMs / 86_400_000), 'day');
}

export function formatAdminNumber(
  value: number,
  options?: Intl.NumberFormatOptions,
  locale?: string,
) {
  return new Intl.NumberFormat(resolveAdminFormattingLocale(locale), options).format(value);
}

export function formatAdminCompactNumber(
  value: number,
  options?: Intl.NumberFormatOptions,
  locale?: string,
) {
  return new Intl.NumberFormat(resolveAdminFormattingLocale(locale), {
    notation: 'compact',
    ...options,
  }).format(value);
}

export function formatAdminPercent(
  value: number,
  options?: Intl.NumberFormatOptions,
  locale?: string,
) {
  return new Intl.NumberFormat(resolveAdminFormattingLocale(locale), {
    style: 'percent',
    ...options,
  }).format(value);
}
