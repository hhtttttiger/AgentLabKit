import '@testing-library/jest-dom/vitest';
import { beforeEach } from 'vitest';
import i18n from '@/shared/i18n';
import { ADMIN_LOCALE_STORAGE_KEY, type AdminLocale } from '@/shared/i18n/config';

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

Object.defineProperty(globalThis, 'ResizeObserver', {
  writable: true,
  configurable: true,
  value: ResizeObserverMock,
});

beforeEach(async () => {
  window.localStorage?.clear?.();
  globalThis.localStorage?.clear?.();
  await i18n.changeLanguage('zh-CN');
});

export async function switchTestLanguage(locale: AdminLocale) {
  window.localStorage?.setItem?.(ADMIN_LOCALE_STORAGE_KEY, locale);
  globalThis.localStorage?.setItem?.(ADMIN_LOCALE_STORAGE_KEY, locale);
  await i18n.changeLanguage(locale);
}
