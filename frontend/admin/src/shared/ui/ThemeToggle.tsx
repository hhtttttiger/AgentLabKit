import { Moon, Sun } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../theme';
import './ThemeToggle.css';

interface ThemeToggleProps {
  placement?: 'sidebar' | 'header' | 'inline';
}

export function ThemeToggle({ placement = 'header' }: ThemeToggleProps) {
  const { t } = useTranslation('common');
  const { resolvedTheme, toggleTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';
  const Icon = isDark ? Sun : Moon;
  const label = isDark ? t('themeToggle.toLight') : t('themeToggle.toDark');

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={label}
      title={label}
      className={`theme-toggle theme-toggle--${placement} accent-transition-target`}
    >
      <Icon size={18} />
    </button>
  );
}
