import { useTranslation } from 'react-i18next';
import { MAX_RADIUS, MIN_RADIUS, useTheme } from '../theme';
import './RadiusSlider.css';

export function RadiusSlider() {
  const { t } = useTranslation('common');
  const { radius, setRadius } = useTheme();

  return (
    <div className="radius-slider">
      <div className="radius-slider__header">
        <span>{t('preferences.radius')}</span>
        <output htmlFor="global-radius" className="radius-slider__value">
          {t('preferences.radiusValue', { value: radius })}
        </output>
      </div>
      <input
        id="global-radius"
        className="radius-slider__input"
        type="range"
        min={MIN_RADIUS}
        max={MAX_RADIUS}
        step={1}
        value={radius}
        onChange={(event) => setRadius(Number(event.target.value))}
        aria-label={t('preferences.radius')}
      />
      <div className="radius-slider__labels" aria-hidden="true">
        <span>{t('preferences.radiusSharp')}</span>
        <span>{t('preferences.radiusSoft')}</span>
      </div>
    </div>
  );
}
