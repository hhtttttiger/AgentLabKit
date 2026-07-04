import {
  FRONTEND_DEFAULT_LOCALE,
  FRONTEND_LOCALE_LABELS,
  FRONTEND_SUPPORTED_LOCALES,
  normalizeFrontendLocale,
} from './frontendLocales';

describe('frontendLocales shared contract', () => {
  it('exports supported locales in stable order', () => {
    expect(FRONTEND_SUPPORTED_LOCALES).toEqual(['zh-CN', 'en-US']);
  });

  it('defaults to zh-CN', () => {
    expect(FRONTEND_DEFAULT_LOCALE).toBe('zh-CN');
  });

  describe('normalizeFrontendLocale', () => {
    it('normalizes Chinese locale variants to zh-CN', () => {
      expect(normalizeFrontendLocale('zh')).toBe('zh-CN');
      expect(normalizeFrontendLocale('zh-CN')).toBe('zh-CN');
      expect(normalizeFrontendLocale('zh-TW')).toBe('zh-CN');
    });

    it('normalizes English locale variants to en-US', () => {
      expect(normalizeFrontendLocale('en')).toBe('en-US');
      expect(normalizeFrontendLocale('en-US')).toBe('en-US');
      expect(normalizeFrontendLocale('en-GB')).toBe('en-US');
    });

    it('falls back to DEFAULT_LOCALE for unknown or empty input including ja', () => {
      expect(normalizeFrontendLocale('ja')).toBe(FRONTEND_DEFAULT_LOCALE);
      expect(normalizeFrontendLocale('ja-JP')).toBe(FRONTEND_DEFAULT_LOCALE);
    });

    it('falls back to DEFAULT_LOCALE for unknown or empty input', () => {
      expect(normalizeFrontendLocale(undefined)).toBe(FRONTEND_DEFAULT_LOCALE);
      expect(normalizeFrontendLocale(null)).toBe(FRONTEND_DEFAULT_LOCALE);
      expect(normalizeFrontendLocale('')).toBe(FRONTEND_DEFAULT_LOCALE);
      expect(normalizeFrontendLocale('fr-FR')).toBe(FRONTEND_DEFAULT_LOCALE);
    });
  });

  it('provides native and short labels for every supported locale', () => {
    for (const locale of FRONTEND_SUPPORTED_LOCALES) {
      expect(FRONTEND_LOCALE_LABELS[locale]).toBeDefined();
      expect(typeof FRONTEND_LOCALE_LABELS[locale].native).toBe('string');
      expect(FRONTEND_LOCALE_LABELS[locale].native.length).toBeGreaterThan(0);
      expect(typeof FRONTEND_LOCALE_LABELS[locale].short).toBe('string');
      expect(FRONTEND_LOCALE_LABELS[locale].short.length).toBeGreaterThan(0);
    }
  });
});
