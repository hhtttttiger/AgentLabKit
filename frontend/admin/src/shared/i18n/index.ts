import i18n from 'i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import { initReactI18next } from 'react-i18next';
import {
  ADMIN_LOCALE_STORAGE_KEY,
  DEFAULT_ADMIN_LOCALE,
  SUPPORTED_ADMIN_LOCALES,
  normalizeAdminLocale,
} from './config';
import { adminI18nResources } from './resources';

function loadInitialLocale() {
  try {
    const stored = globalThis.localStorage?.getItem(ADMIN_LOCALE_STORAGE_KEY);
    return stored ? normalizeAdminLocale(stored) : undefined;
  } catch {
    return undefined;
  }
}

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: adminI18nResources,
    defaultNS: 'common',
    ns: ['common'],
    lng: loadInitialLocale(),
    fallbackLng: DEFAULT_ADMIN_LOCALE,
    supportedLngs: [...SUPPORTED_ADMIN_LOCALES],
    interpolation: {
      escapeValue: false,
    },
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      lookupLocalStorage: ADMIN_LOCALE_STORAGE_KEY,
      caches: [],
      convertDetectedLanguage: (value: string) => normalizeAdminLocale(value),
    },
  });

export default i18n;
