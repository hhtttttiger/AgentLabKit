import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '@/shared/i18n';
import { DocumentLanguageSync } from '@/shared/i18n/DocumentLanguageSync';
import { createStorageMock } from '@/shared/test/storage';
import { ThemeProvider } from '@/shared/theme';
import { LoginPage } from './LoginPage';

vi.mock('@/shared/auth', () => ({
  useAuth: () => ({
    isAuthenticated: false,
    login: vi.fn(),
  }),
}));

describe('LoginPage localization', () => {
  beforeEach(async () => {
    const storage = createStorageMock();
    vi.stubGlobal('localStorage', storage);
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      writable: true,
      value: storage,
    });
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
    await i18n.changeLanguage('en-US');
  });

  function renderLoginPage() {
    return render(
      <MemoryRouter>
        <ThemeProvider>
          <DocumentLanguageSync />
          <LoginPage />
        </ThemeProvider>
      </MemoryRouter>,
    );
  }

  it('renders English copy when locale is en-US', () => {
    renderLoginPage();

    expect(screen.getByLabelText('Username')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Log in' })).toBeInTheDocument();
  });

  it('renders the login preferences footer before sign-in', () => {
    renderLoginPage();

    const trigger = screen.getByRole('button', { name: /Login preferences/i });
    expect(screen.getByRole('group', { name: 'Login preferences' })).toBeInTheDocument();
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByRole('dialog', { name: /Login preference controls/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'English' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Blue (default)' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Switch to dark mode' })).not.toBeInTheDocument();
  });

  it('opens the preferences popover and keeps it open while changing locale and accent', async () => {
    const user = userEvent.setup();

    renderLoginPage();

    await user.click(screen.getByRole('button', { name: /Login preferences/i }));

    expect(screen.getByRole('dialog', { name: /Login preference controls/i })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Rose' }));

    await waitFor(() => {
      expect(localStorage.getItem('agentlabkit-accent')).toBe('rose');
    });

    expect(screen.getByRole('dialog', { name: /Login preference controls/i })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '简体中文' }));

    await waitFor(() => {
      expect(document.documentElement.lang).toBe('zh-CN');
      expect(localStorage.getItem('agentlabkit-locale')).toBe('zh-CN');
    });

    expect(screen.getByRole('dialog', { name: '登录偏好设置面板' })).toBeInTheDocument();
  });

  it('persists locale switching and updates the login copy before sign-in', async () => {
    const user = userEvent.setup();

    renderLoginPage();

    await user.click(screen.getByRole('button', { name: /Login preferences/i }));
    await user.click(screen.getByRole('button', { name: '简体中文' }));

    await waitFor(() => {
      expect(screen.getByLabelText('用户名')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '登录' })).toBeInTheDocument();
      expect(localStorage.getItem('agentlabkit-locale')).toBe('zh-CN');
      expect(document.documentElement.lang).toBe('zh-CN');
    });
  });

  it('persists accent switching before sign-in', async () => {
    const user = userEvent.setup();

    renderLoginPage();

    await user.click(screen.getByRole('button', { name: /Login preferences/i }));
    await user.click(screen.getByRole('button', { name: 'Rose' }));

    await waitFor(() => {
      expect(localStorage.getItem('agentlabkit-accent')).toBe('rose');
      expect(document.documentElement.getAttribute('data-accent')).toBe('rose');
      expect(screen.getByRole('button', { name: 'Rose' })).toHaveAttribute('aria-pressed', 'true');
    });
  });

  it('closes the preferences popover with Escape and returns focus to the trigger', async () => {
    const user = userEvent.setup();

    renderLoginPage();

    const trigger = screen.getByRole('button', { name: /Login preferences/i });
    trigger.focus();

    await user.keyboard('{Enter}');
    expect(screen.getByRole('dialog', { name: /Login preference controls/i })).toBeInTheDocument();

    await user.keyboard('{Escape}');

    expect(screen.queryByRole('dialog', { name: /Login preference controls/i })).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it('closes the preferences popover when clicking outside', async () => {
    const user = userEvent.setup();

    render(
      <>
        <MemoryRouter>
          <ThemeProvider>
            <DocumentLanguageSync />
            <LoginPage />
          </ThemeProvider>
        </MemoryRouter>
        <button type="button">Outside action</button>
      </>,
    );

    await user.click(screen.getByRole('button', { name: /Login preferences/i }));
    expect(screen.getByRole('dialog', { name: /Login preference controls/i })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Outside action' }));

    expect(screen.queryByRole('dialog', { name: /Login preference controls/i })).not.toBeInTheDocument();
  });

  it('keeps the summary trigger visible while the detailed controls stay hidden until opened', () => {
    renderLoginPage();

    expect(screen.getByRole('button', { name: /Open login preferences/i })).toBeInTheDocument();
    expect(screen.queryByText('Interface')).not.toBeInTheDocument();
    expect(screen.queryByText('Language, accent, and theme')).not.toBeInTheDocument();
    expect(screen.queryByText('Language')).not.toBeInTheDocument();
    expect(screen.queryByText('Accent')).not.toBeInTheDocument();
  });

  it('updates the trigger accessibility label when the preferences popover is open', async () => {
    const user = userEvent.setup();

    renderLoginPage();

    const trigger = screen.getByRole('button', { name: /Open login preferences/i });
    await user.click(trigger);

    expect(screen.getByRole('button', { name: /Close login preferences/i })).toHaveAttribute('aria-expanded', 'true');
  });
});
