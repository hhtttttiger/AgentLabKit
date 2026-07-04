import { useTranslation } from 'react-i18next';
import type { AccentColor } from '../theme';
import { useTheme } from '../theme';
import './AccentPicker.css';

interface AccentOption {
  value: AccentColor;
  /** CSS color value for the swatch — matches the 500-level hue */
  color: string;
}

const ACCENT_OPTIONS: AccentOption[] = [
  { value: 'blue', color: '#3b82f6' },
  { value: 'violet', color: '#8b5cf6' },
  { value: 'emerald', color: '#10b981' },
  { value: 'rose', color: '#f43f5e' },
  { value: 'amber', color: '#f59e0b' },
  { value: 'orange', color: '#ff6900' },
];

interface AccentPickerProps {
  className?: string;
}

export function AccentPicker({ className }: AccentPickerProps) {
  const { t } = useTranslation('common');
  const { accent, setAccent } = useTheme();

  return (
    <div
      className={['accent-picker', 'accent-transition-target', className].filter(Boolean).join(' ')}
      role="group"
      aria-label={t('preferences.accent')}
    >
      {ACCENT_OPTIONS.map((opt) => {
        const label = t(`preferences.accentOptions.${opt.value}`);
        return (
        <button
          key={opt.value}
          type="button"
          title={label}
          aria-label={label}
          aria-pressed={accent === opt.value}
          className={`accent-picker__dot${accent === opt.value ? ' accent-picker__dot--active' : ''}`}
          style={{ '--dot-color': opt.color } as React.CSSProperties}
          onClick={() => setAccent(opt.value)}
        />
        );
      })}
    </div>
  );
}
