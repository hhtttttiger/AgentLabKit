export const FRONTEND_SUPPORTED_LOCALES = ['zh-CN', 'en-US'] as const;
export const FRONTEND_DEFAULT_LOCALE = 'zh-CN' as const;

export type FrontendLocale = (typeof FRONTEND_SUPPORTED_LOCALES)[number];

export const FRONTEND_LOCALE_LABELS = {
  'zh-CN': { native: '简体中文', short: '中文' },
  'en-US': { native: 'English', short: 'EN' },
} as const satisfies Record<FrontendLocale, { native: string; short: string }>;

export function normalizeFrontendLocale(value?: string | null): FrontendLocale {
  const normalized = value?.trim().toLowerCase();
  if (!normalized) return FRONTEND_DEFAULT_LOCALE;
  if (normalized.startsWith('zh')) return 'zh-CN';
  if (normalized.startsWith('en')) return 'en-US';
  return FRONTEND_DEFAULT_LOCALE;
}
