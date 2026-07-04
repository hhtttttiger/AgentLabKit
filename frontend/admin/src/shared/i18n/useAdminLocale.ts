import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ADMIN_LOCALE_STORAGE_KEY,
  SUPPORTED_ADMIN_LOCALES,
  normalizeAdminLocale,
  type AdminLocale,
} from './config';

export function useAdminLocale() {
  const { i18n } = useTranslation('common');
  const locale = normalizeAdminLocale(i18n.resolvedLanguage ?? i18n.language);

  const setLocale = useCallback(
    async (value: AdminLocale) => {
      try {
        localStorage.setItem(ADMIN_LOCALE_STORAGE_KEY, value);
      } catch {
        // Ignore storage write failures; the active session still updates via i18n.
      }
      await i18n.changeLanguage(value);
    },
    [i18n],
  );

  return {
    locale,
    setLocale,
    supportedLocales: SUPPORTED_ADMIN_LOCALES,
  };
}
