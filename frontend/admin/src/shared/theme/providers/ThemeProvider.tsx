import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import type { Theme, ResolvedTheme, AccentColor, ThemeContextValue } from '../types';

const ThemeContext = createContext<ThemeContextValue | null>(null);

const STORAGE_KEY = 'agentlabkit-theme';
const ACCENT_STORAGE_KEY = 'agentlabkit-accent';
const RADIUS_STORAGE_KEY = 'agentlabkit-radius';
export const DEFAULT_RADIUS = 2;
export const MIN_RADIUS = 0;
export const MAX_RADIUS = 20;

const VALID_ACCENTS: AccentColor[] = ['blue', 'violet', 'emerald', 'rose', 'amber', 'orange'];

function getStoredTheme(): Theme {
  if (typeof window === 'undefined') {
    return 'system';
  }

  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored === 'light' || stored === 'dark' || stored === 'system' ? stored : 'system';
  } catch {
    return 'system';
  }
}

function getSystemTheme(): ResolvedTheme {
  if (typeof window === 'undefined') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function getStoredAccent(): AccentColor {
  if (typeof window === 'undefined') return 'blue';
  try {
    const stored = window.localStorage.getItem(ACCENT_STORAGE_KEY);
    return VALID_ACCENTS.includes(stored as AccentColor) ? (stored as AccentColor) : 'blue';
  } catch {
    return 'blue';
  }
}

function getStoredRadius(): number {
  if (typeof window === 'undefined') return DEFAULT_RADIUS;
  try {
    const storedValue = window.localStorage.getItem(RADIUS_STORAGE_KEY);
    if (storedValue === null || storedValue.trim() === '') return DEFAULT_RADIUS;
    const stored = Number(storedValue);
    return Number.isFinite(stored) ? Math.min(MAX_RADIUS, Math.max(MIN_RADIUS, stored)) : DEFAULT_RADIUS;
  } catch {
    return DEFAULT_RADIUS;
  }
}

function applyTheme(nextTheme: ResolvedTheme) {
  const root = document.documentElement;
  root.setAttribute('data-theme', nextTheme);
  root.style.colorScheme = nextTheme;
}

function applyAccent(nextAccent: AccentColor) {
  const root = document.documentElement;
  if (nextAccent === 'blue') {
    root.removeAttribute('data-accent');
  } else {
    root.setAttribute('data-accent', nextAccent);
  }
}

function applyRadius(nextRadius: number) {
  document.documentElement.style.setProperty('--radius-global', `${nextRadius}px`);
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(getStoredTheme);
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>(() => {
    const initialTheme = getStoredTheme();
    return initialTheme === 'system' ? getSystemTheme() : initialTheme;
  });
  const [accent, setAccentState] = useState<AccentColor>(getStoredAccent);
  const [radius, setRadiusState] = useState<number>(getStoredRadius);

  useEffect(() => {
    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const nextResolvedTheme = mediaQuery.matches ? 'dark' : 'light';
      setResolvedTheme(nextResolvedTheme);
      applyTheme(nextResolvedTheme);

      const handleChange = (event: MediaQueryListEvent) => {
        const updatedTheme = event.matches ? 'dark' : 'light';
        setResolvedTheme(updatedTheme);
        applyTheme(updatedTheme);
      };

      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }

    setResolvedTheme(theme);
    applyTheme(theme);

    return undefined;
  }, [theme]);

  useEffect(() => {
    applyAccent(accent);
  }, [accent]);

  useEffect(() => {
    applyRadius(radius);
  }, [radius]);

  const setTheme = useCallback((newTheme: Theme) => {
    setThemeState(newTheme);
    try {
      window.localStorage.setItem(STORAGE_KEY, newTheme);
    } catch {
      // Ignore storage write failures; the active session still updates via React state.
    }
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme(resolvedTheme === 'dark' ? 'light' : 'dark');
  }, [resolvedTheme, setTheme]);

  const setAccent = useCallback((newAccent: AccentColor) => {
    setAccentState(newAccent);
    try {
      window.localStorage.setItem(ACCENT_STORAGE_KEY, newAccent);
    } catch {
      // Ignore storage write failures; the active session still updates via React state.
    }
  }, []);

  const setRadius = useCallback((newRadius: number) => {
    const nextRadius = Math.min(MAX_RADIUS, Math.max(MIN_RADIUS, Math.round(newRadius)));
    setRadiusState(nextRadius);
    try {
      window.localStorage.setItem(RADIUS_STORAGE_KEY, String(nextRadius));
    } catch {
      // Ignore storage write failures; the active session still updates via React state.
    }
  }, []);

  return (
    <ThemeContext.Provider
      value={{ theme, resolvedTheme, setTheme, toggleTheme, accent, setAccent, radius, setRadius }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}
