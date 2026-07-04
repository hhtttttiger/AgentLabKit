import { useEffect } from 'react';
import i18n from './index';
import { normalizeAdminLocale } from './config';

export function DocumentLanguageSync() {
  useEffect(() => {
    const apply = (value: string) => {
      const locale = normalizeAdminLocale(value);
      document.documentElement.lang = locale;
      document.documentElement.dataset.locale = locale;
    };

    apply(i18n.resolvedLanguage ?? i18n.language);
    i18n.on('languageChanged', apply);

    return () => {
      i18n.off('languageChanged', apply);
    };
  }, []);

  return null;
}
