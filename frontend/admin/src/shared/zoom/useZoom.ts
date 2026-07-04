import { useCallback, useEffect, useState } from 'react';

export type ZoomLevel = 'auto' | '100' | '90' | '80';

const STORAGE_KEY = 'agentlabkit-zoom';
const VALID_LEVELS: ZoomLevel[] = ['auto', '100', '90', '80'];

/** Maps ZoomLevel to the CSS zoom value; null means "remove inline style, let CSS handle it". */
const ZOOM_VALUES: Record<ZoomLevel, string | null> = {
  auto: null,
  '100': '1',
  '90':  '0.9',
  '80':  '0.8',
};

function load(): ZoomLevel {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    return VALID_LEVELS.includes(v as ZoomLevel) ? (v as ZoomLevel) : 'auto';
  } catch {
    return 'auto';
  }
}

function apply(level: ZoomLevel) {
  if (typeof document === 'undefined') return;
  const value = ZOOM_VALUES[level];
  if (value === null) {
    document.documentElement.style.removeProperty('zoom');
    document.documentElement.style.removeProperty('min-height');
  } else {
    const zoomNum = parseFloat(value);
    document.documentElement.style.zoom = value;
    // Compensate: zoom scales the rendered box down, leaving blank space below.
    // Setting min-height to (100vh / zoom) makes the visual height fill the viewport exactly.
    document.documentElement.style.minHeight = `${(100 / zoomNum).toFixed(4)}vh`;
  }
}

/**
 * Apply synchronously on module import to prevent a layout flash before
 * React hydrates — same pattern as useMotion.
 */
apply(load());

export function useZoom() {
  const [zoomLevel, setZoomLevelState] = useState<ZoomLevel>(load);

  useEffect(() => {
    apply(zoomLevel);
    try { localStorage.setItem(STORAGE_KEY, zoomLevel); } catch { /* ignore */ }
  }, [zoomLevel]);

  const setZoomLevel = useCallback((level: ZoomLevel) => {
    setZoomLevelState(level);
  }, []);

  return { zoomLevel, setZoomLevel };
}
