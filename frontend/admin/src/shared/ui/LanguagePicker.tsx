import type { AdminLocale } from '@/shared/i18n/config';
import { useTranslation } from 'react-i18next';
import { useAdminLocale } from '@/shared/i18n/useAdminLocale';
import './LanguagePicker.css';

interface LanguagePickerProps {
  className?: string;
  onSelect?: (locale: AdminLocale) => void;
  shouldNotifySelection?: (locale: AdminLocale) => boolean;
}

export function LanguagePicker({ className, onSelect, shouldNotifySelection }: LanguagePickerProps) {
  const { t } = useTranslation('common');
  const { locale, setLocale, supportedLocales } = useAdminLocale();

  async function handleSelect(value: AdminLocale) {
    await setLocale(value);
    if (shouldNotifySelection && !shouldNotifySelection(value)) {
      return;
    }
    onSelect?.(value);
  }

  return (
    <div
      className={['language-picker', className].filter(Boolean).join(' ')}
      role="group"
      aria-label={t('preferences.language.label')}
    >
      {supportedLocales.map((value) => {
        const active = value === locale;
        return (
          <button
            key={value}
            type="button"
            className={`language-picker__option${active ? ' language-picker__option--active' : ''}`}
            aria-pressed={active}
            onClick={() => { void handleSelect(value); }}
          >
            {t(`preferences.language.options.${value}`)}
          </button>
        );
      })}
    </div>
  );
}
