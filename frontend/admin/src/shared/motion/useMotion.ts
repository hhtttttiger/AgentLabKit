import { useCallback, useEffect, useState } from 'react';

const STORAGE_KEY = 'agentlabkit-motion';
const HTML_CLASS = 'motion-enabled';

function load(): boolean {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    return v === null ? true : v === 'true'; // default ON
  } catch {
    return true;
  }
}

/**
 * Applies the `motion-enabled` class to `<html>` synchronously on module import
 * to prevent a flash of unanimated → animated content before React hydrates.
 * This is an intentional import side effect — call sites need not do anything extra.
 */
if (typeof document !== 'undefined' && load()) {
  document.documentElement.classList.add(HTML_CLASS);
}

export function useMotion() {
  const [enabled, setEnabled] = useState(load);

  useEffect(() => {
    if (enabled) {
      document.documentElement.classList.add(HTML_CLASS);
    } else {
      document.documentElement.classList.remove(HTML_CLASS);
    }
    try { localStorage.setItem(STORAGE_KEY, String(enabled)); } catch { /* ignore */ }
  }, [enabled]);

  const toggle = useCallback(() => setEnabled((v) => !v), []);

  return { motionEnabled: enabled, toggleMotion: toggle };
}
