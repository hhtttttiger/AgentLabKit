import { describe, expect, it } from 'vitest';
import { DEFAULT_ADMIN_LOCALE, normalizeAdminLocale, SUPPORTED_ADMIN_LOCALES } from './config';

describe('admin i18n config', () => {
  it('normalizes browser-style English locales to en-US', () => {
    expect(normalizeAdminLocale('en')).toBe('en-US');
    expect(normalizeAdminLocale('en-GB')).toBe('en-US');
  });

  it('normalizes browser-style Chinese and English locales to canonical codes', () => {
    expect(normalizeAdminLocale('zh')).toBe('zh-CN');
    expect(normalizeAdminLocale('zh-TW')).toBe('zh-CN');
    expect(normalizeAdminLocale('en')).toBe('en-US');
    expect(normalizeAdminLocale('en-GB')).toBe('en-US');
  });

  it('falls back to zh-CN for unknown or empty locales', () => {
    expect(normalizeAdminLocale('')).toBe(DEFAULT_ADMIN_LOCALE);
    expect(normalizeAdminLocale('fr-FR')).toBe(DEFAULT_ADMIN_LOCALE);
    expect(normalizeAdminLocale('ja')).toBe(DEFAULT_ADMIN_LOCALE);
    expect(normalizeAdminLocale('ja-JP')).toBe(DEFAULT_ADMIN_LOCALE);
    expect(normalizeAdminLocale(undefined)).toBe(DEFAULT_ADMIN_LOCALE);
  });

  it('publishes the supported locale list in stable order', () => {
    expect(SUPPORTED_ADMIN_LOCALES).toEqual(['zh-CN', 'en-US']);
  });
});
