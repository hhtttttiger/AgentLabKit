import { afterEach, describe, expect, it } from 'vitest';
import { switchTestLanguage } from '@/shared/test/setup';
import i18n from './index';
import {
  formatAdminCompactNumber,
  formatAdminDate,
  formatAdminDateTime,
  formatAdminNumber,
  formatAdminPercent,
  formatAdminRelativeTime,
  formatAdminTime,
  getAdminFormattingLocale,
} from './formatters';

describe('shared admin formatters', () => {
  const originalResolvedLanguage = i18n.resolvedLanguage;
  const originalLanguage = i18n.language;

  afterEach(async () => {
    Object.defineProperty(i18n, 'resolvedLanguage', {
      configurable: true,
      writable: true,
      value: originalResolvedLanguage,
    });
    Object.defineProperty(i18n, 'language', {
      configurable: true,
      writable: true,
      value: originalLanguage,
    });
    await switchTestLanguage('zh-CN');
  });

  it('prefers resolvedLanguage and falls back to language', () => {
    Object.defineProperty(i18n, 'resolvedLanguage', {
      configurable: true,
      writable: true,
      value: 'en-US',
    });
    Object.defineProperty(i18n, 'language', {
      configurable: true,
      writable: true,
      value: 'zh-CN',
    });

    expect(getAdminFormattingLocale()).toBe('en-US');

    Object.defineProperty(i18n, 'resolvedLanguage', {
      configurable: true,
      writable: true,
      value: undefined,
    });

    expect(getAdminFormattingLocale()).toBe('zh-CN');
  });

  it('formats date values with the active locale', async () => {
    const value = '2026-01-02T03:04:05Z';
    const options: Intl.DateTimeFormatOptions = {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    };

    await switchTestLanguage('zh-CN');
    const zhValue = formatAdminDateTime(value, options);
    expect(zhValue).toBe(new Intl.DateTimeFormat('zh-CN', options).format(new Date(value)));

    await switchTestLanguage('en-US');
    const enValue = formatAdminDateTime(value, options);
    expect(enValue).toBe(new Intl.DateTimeFormat('en-US', options).format(new Date(value)));
    expect(enValue).not.toBe(zhValue);
  });

  it('defaults to locale date and time formatting when no options are provided', async () => {
    const value = '2026-01-02T03:04:05Z';

    await switchTestLanguage('zh-CN');
    expect(formatAdminDateTime(value)).toBe(new Date(value).toLocaleString('zh-CN'));

    await switchTestLanguage('en-US');
    expect(formatAdminDateTime(value)).toBe(new Date(value).toLocaleString('en-US'));
  });

  it('formats date-only and time-only values with the active locale', async () => {
    const value = '2026-01-02T03:04:05Z';

    await switchTestLanguage('zh-CN');
    expect(formatAdminDate(value)).toBe(new Date(value).toLocaleDateString('zh-CN'));
    expect(formatAdminTime(value)).toBe(new Date(value).toLocaleTimeString('zh-CN'));

    await switchTestLanguage('en-US');
    expect(formatAdminDate(value)).toBe(new Date(value).toLocaleDateString('en-US'));
    expect(formatAdminTime(value)).toBe(new Date(value).toLocaleTimeString('en-US'));
  });

  it('formats relative timestamps with the active locale and falls back to dates for older values', async () => {
    const now = '2026-04-14T08:09:10Z';
    const recentValue = '2026-04-14T08:06:10Z';
    const olderValue = '2026-04-06T08:09:10Z';

    await switchTestLanguage('zh-CN');
    expect(formatAdminRelativeTime(recentValue, { now })).toBe(
      new Intl.RelativeTimeFormat('zh-CN', { numeric: 'auto' }).format(-3, 'minute'),
    );
    expect(formatAdminRelativeTime(olderValue, { now })).toBe(
      new Date(olderValue).toLocaleDateString('zh-CN'),
    );

    await switchTestLanguage('en-US');
    expect(formatAdminRelativeTime(recentValue, { now })).toBe(
      new Intl.RelativeTimeFormat('en-US', { numeric: 'auto' }).format(-3, 'minute'),
    );
    expect(formatAdminRelativeTime(olderValue, { now })).toBe(
      new Date(olderValue).toLocaleDateString('en-US'),
    );
  });

  it('formats numbers, compact numbers, and percent values with the active locale', async () => {
    await switchTestLanguage('zh-CN');
    const zhCompact = formatAdminCompactNumber(1_234_000, { maximumFractionDigits: 1 });

    expect(formatAdminNumber(1_234_567.89, { maximumFractionDigits: 2 })).toBe(
      new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 2 }).format(1_234_567.89),
    );
    expect(zhCompact).toBe(
      new Intl.NumberFormat('zh-CN', { notation: 'compact', maximumFractionDigits: 1 }).format(1_234_000),
    );
    expect(formatAdminPercent(0.256, { minimumFractionDigits: 1, maximumFractionDigits: 1 })).toBe(
      new Intl.NumberFormat('zh-CN', {
        style: 'percent',
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      }).format(0.256),
    );

    await switchTestLanguage('en-US');
    const enCompact = formatAdminCompactNumber(1_234_000, { maximumFractionDigits: 1 });

    expect(formatAdminNumber(1_234_567.89, { maximumFractionDigits: 2 })).toBe(
      new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(1_234_567.89),
    );
    expect(enCompact).toBe(
      new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(1_234_000),
    );
    expect(formatAdminPercent(0.256, { minimumFractionDigits: 1, maximumFractionDigits: 1 })).toBe(
      new Intl.NumberFormat('en-US', {
        style: 'percent',
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      }).format(0.256),
    );
    expect(enCompact).not.toBe(zhCompact);
  });

  it('allows locale overrides without depending on the active language', () => {
    const value = '2026-01-02T03:04:05Z';

    expect(formatAdminDateTime(value, undefined, 'en-US')).toBe(new Date(value).toLocaleString('en-US'));
    expect(formatAdminDate(value, undefined, 'en-US')).toBe(new Date(value).toLocaleDateString('en-US'));
    expect(formatAdminTime(value, undefined, 'en-US')).toBe(new Date(value).toLocaleTimeString('en-US'));
    expect(formatAdminNumber(1234.5, undefined, 'en-US')).toBe(new Intl.NumberFormat('en-US').format(1234.5));
    expect(formatAdminCompactNumber(1234_000, undefined, 'en-US')).toBe(
      new Intl.NumberFormat('en-US', { notation: 'compact' }).format(1234_000),
    );
    expect(formatAdminPercent(0.25, undefined, 'en-US')).toBe(new Intl.NumberFormat('en-US', { style: 'percent' }).format(0.25));
  });

  it('returns a placeholder for empty date values', () => {
    expect(formatAdminDateTime(null)).toBe('-');
    expect(formatAdminDateTime(undefined)).toBe('-');
  });
});
