import { useZoom, type ZoomLevel } from '../zoom/useZoom';
import './ZoomSlider.css';

const STOPS: { value: ZoomLevel; label: string }[] = [
  { value: 'auto', label: '自动' },
  { value: '100',  label: '100%' },
  { value: '90',   label: '90%'  },
  { value: '80',   label: '80%'  },
];

const STOP_COUNT = STOPS.length;

function stopIndex(level: ZoomLevel): number {
  return STOPS.findIndex((s) => s.value === level);
}

export function ZoomSlider() {
  const { zoomLevel, setZoomLevel } = useZoom();
  const activeIdx = stopIndex(zoomLevel);
  const fillPct = (activeIdx / (STOP_COUNT - 1)) * 100;

  return (
    <div className="zoom-slider" aria-label="缩放比例">
      {/* Track */}
      <div className="zoom-slider__track-wrap">
        {/* Filled rail */}
        <div
          className="zoom-slider__fill"
          style={{ width: `${fillPct}%` }}
        />

        {/* Stops */}
        {STOPS.map((stop, idx) => {
          const pct = (idx / (STOP_COUNT - 1)) * 100;
          const isActive = idx === activeIdx;
          return (
            <button
              key={stop.value}
              type="button"
              aria-pressed={isActive}
              aria-label={stop.label}
              className={[
                'zoom-slider__stop',
                isActive ? 'zoom-slider__stop--active' : '',
              ].join(' ')}
              style={{ left: `${pct}%` }}
              onClick={() => setZoomLevel(stop.value)}
            />
          );
        })}

        {/* Thumb (on top of the active stop) */}
        <div
          className="zoom-slider__thumb"
          style={{ left: `${fillPct}%` }}
          aria-hidden
        />
      </div>

      {/* Labels */}
      <div className="zoom-slider__labels">
        {STOPS.map((stop, idx) => {
          const pct = (idx / (STOP_COUNT - 1)) * 100;
          return (
            <span
              key={stop.value}
              className={`zoom-slider__label${idx === activeIdx ? ' zoom-slider__label--active' : ''}`}
              style={{ left: `${pct}%` }}
            >
              {stop.label}
            </span>
          );
        })}
      </div>
    </div>
  );
}
