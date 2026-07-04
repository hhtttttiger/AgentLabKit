import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createStorageMock } from '@/shared/test/storage';
import { AccentPicker } from '@/shared/ui/AccentPicker';
import { ThemeToggle } from '@/shared/ui/ThemeToggle';
import { ThemeProvider, useTheme } from '..';

function AccentConsumer() {
  const { accent, setAccent } = useTheme();

  return (
    <button
      type="button"
      aria-label="Set rose accent"
      aria-pressed={accent === 'rose'}
      onClick={() => setAccent('rose')}
    >
      Set rose accent
    </button>
  );
}

function ThemeConsumer() {
  const { theme, resolvedTheme, accent, toggleTheme } = useTheme();

  return (
    <>
      <div data-testid="theme-value">{theme}</div>
      <div data-testid="resolved-theme-value">{resolvedTheme}</div>
      <div data-testid="accent-value">{accent}</div>
      <button type="button" onClick={toggleTheme}>
        Toggle theme
      </button>
    </>
  );
}

function AccentTransitionConsumers() {
  return (
    <>
      <AccentPicker />
      <ThemeToggle placement="inline" />
    </>
  );
}

describe('ThemeProvider storage fallbacks', () => {
  beforeEach(() => {
    const storage = createStorageMock();
    vi.stubGlobal('localStorage', storage);
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      writable: true,
      value: storage,
    });
    vi.stubGlobal(
      'matchMedia',
      vi.fn().mockReturnValue({
        matches: false,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }),
    );
    document.documentElement.removeAttribute('data-theme');
    document.documentElement.removeAttribute('data-accent');
    document.documentElement.style.colorScheme = '';
  });

  it('mounts with safe defaults when localStorage reads throw', async () => {
    window.localStorage.getItem = vi.fn(() => {
      throw new Error('blocked');
    });

    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('theme-value')).toHaveTextContent('system');
      expect(screen.getByTestId('resolved-theme-value')).toHaveTextContent('light');
      expect(screen.getByTestId('accent-value')).toHaveTextContent('blue');
      expect(document.documentElement.getAttribute('data-theme')).toBe('light');
      expect(document.documentElement.getAttribute('data-accent')).toBeNull();
    });
  });

  it('updates the active theme when localStorage persistence throws', async () => {
    const user = userEvent.setup();
    const originalSetItem = window.localStorage.setItem.bind(window.localStorage);

    window.localStorage.setItem = vi.fn((key: string, value: string) => {
      if (key === 'agentlabkit-theme') {
        throw new Error('blocked');
      }
      originalSetItem(key, value);
    });

    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>,
    );

    await expect(user.click(screen.getByRole('button', { name: 'Toggle theme' }))).resolves.toBeUndefined();

    await waitFor(() => {
      expect(screen.getByTestId('theme-value')).toHaveTextContent('dark');
      expect(screen.getByTestId('resolved-theme-value')).toHaveTextContent('dark');
      expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
      expect(document.documentElement.style.colorScheme).toBe('dark');
    });
  });

  it('updates the active accent when localStorage persistence throws', async () => {
    const user = userEvent.setup();
    const originalSetItem = window.localStorage.setItem.bind(window.localStorage);

    window.localStorage.setItem = vi.fn((key: string, value: string) => {
      if (key === 'agentlabkit-accent') {
        throw new Error('blocked');
      }
      originalSetItem(key, value);
    });

    render(
      <ThemeProvider>
        <AccentConsumer />
      </ThemeProvider>,
    );

    await expect(user.click(screen.getByRole('button', { name: 'Set rose accent' }))).resolves.toBeUndefined();

    await waitFor(() => {
      expect(document.documentElement.getAttribute('data-accent')).toBe('rose');
      expect(screen.getByRole('button', { name: 'Set rose accent' })).toHaveAttribute('aria-pressed', 'true');
    });
  });

  it('keeps scoped accent transition hooks on allowed controls without adding a second root motion class', () => {
    document.documentElement.classList.add('motion-enabled');

    render(
      <ThemeProvider>
        <AccentTransitionConsumers />
      </ThemeProvider>,
    );

    expect(document.documentElement).toHaveClass('motion-enabled');
    expect(document.documentElement).not.toHaveClass('accent-transition-enabled');
    expect(document.querySelector('.accent-picker')).toHaveClass('accent-transition-target');
    expect(screen.getByRole('button', { name: /dark mode|深色模式/i })).toHaveClass('accent-transition-target');
  });
});
