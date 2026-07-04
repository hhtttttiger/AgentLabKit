/**
 * i18n resource bundle — assembled from per-locale files.
 *
 * Each locale lives in ./locales/<lang>.ts for better editor performance
 * and clearer ownership. This file re-exports them in the shape i18next expects.
 *
 * To add a new locale:
 *  1. Create ./locales/<lang>.ts exporting `common`
 *  2. Add the entry below
 *  3. Register it in frontendLocales.ts
 */
import { common as zhCN } from './locales/zh-CN';
import { common as enUS } from './locales/en-US';

export const adminI18nResources = {
  'zh-CN': { common: zhCN },
  'en-US': { common: enUS },
} as const;
