import {
  FRONTEND_DEFAULT_LOCALE,
  FRONTEND_SUPPORTED_LOCALES,
  normalizeFrontendLocale,
  type FrontendLocale,
} from './frontendLocales';

export const ADMIN_LOCALE_STORAGE_KEY = 'agentlabkit-locale';
export const DEFAULT_ADMIN_LOCALE = FRONTEND_DEFAULT_LOCALE;
export const SUPPORTED_ADMIN_LOCALES = FRONTEND_SUPPORTED_LOCALES;

export type AdminLocale = FrontendLocale;

export const normalizeAdminLocale = normalizeFrontendLocale;
