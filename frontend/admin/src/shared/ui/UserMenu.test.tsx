import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '@/shared/i18n';
import { DocumentLanguageSync } from '@/shared/i18n/DocumentLanguageSync';
import { ThemeProvider } from '@/shared/theme';
import { createStorageMock } from '@/shared/test/storage';
import { UserMenu } from './UserMenu';

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((promiseResolve) => {
    resolve = promiseResolve;
  });

  return { promise, resolve };
}

function renderUserMenu(extraContent?: ReactNode) {
  return render(
    <>
      <ThemeProvider>
        <DocumentLanguageSync />
        <UserMenu displayName="Admin User" onLogout={vi.fn()} />
      </ThemeProvider>
      {extraContent}
    </>,
  );
}

describe('UserMenu', () => {
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
    document.documentElement.lang = 'zh-CN';
    document.documentElement.dataset.locale = 'zh-CN';
    document.documentElement.removeAttribute('data-theme');
    document.documentElement.removeAttribute('data-accent');
    document.documentElement.classList.remove('motion-enabled');
    await i18n.changeLanguage('zh-CN');
  });

  it('opens a popover panel without menu semantics before drilling into subviews', async () => {
    const user = userEvent.setup();

    renderUserMenu();

    const trigger = screen.getByRole('button', { name: '用户菜单' });
    expect(trigger).not.toHaveAttribute('aria-haspopup');
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    expect(trigger).not.toHaveAttribute('aria-controls');

    await user.click(trigger);

    const rootPanel = trigger.getAttribute('aria-controls');
    expect(rootPanel).toBeTruthy();
    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    expect(trigger).not.toHaveAttribute('aria-haspopup');
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    expect(screen.queryAllByRole('menuitem')).toHaveLength(0);
    expect(document.getElementById(rootPanel ?? '')).toHaveClass('user-menu__dropdown');
    expect(screen.getByText('Admin User')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Language/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '界面偏好' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '登出' })).toBeInTheDocument();

    expect(screen.queryByRole('button', { name: '深色模式' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '开启动画' })).not.toBeInTheDocument();
    expect(screen.queryByLabelText('蓝色（默认）')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('缩放比例')).not.toBeInTheDocument();
  });

  it('drills into language view and persists locale changes', async () => {
    const user = userEvent.setup();

    renderUserMenu();

    const trigger = screen.getByRole('button', { name: '用户菜单' });
    trigger.focus();

    await user.keyboard('{Enter}');

    const languageItem = screen.getByRole('button', { name: /Language/i });
    expect(languageItem).toHaveFocus();

    await user.keyboard('{Enter}');

    const backButton = screen.getByRole('button', { name: '返回' });
    expect(backButton).toHaveFocus();

    await user.tab();
    await user.tab();
    expect(screen.getByRole('button', { name: 'English' })).toHaveFocus();
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(document.documentElement.lang).toBe('en-US');
      expect(localStorage.getItem('agentlabkit-locale')).toBe('en-US');
    });

    expect(screen.getByRole('button', { name: /Language/i })).toHaveFocus();
    expect(screen.getByRole('button', { name: 'Preferences' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'User menu' })).toBeInTheDocument();
  });

  it('drills into preferences view and renders the preference controls there', async () => {
    const user = userEvent.setup();

    renderUserMenu();

    const trigger = screen.getByRole('button', { name: '用户菜单' });
    trigger.focus();

    await user.keyboard('{Enter}');
    expect(screen.getByRole('button', { name: /Language/i })).toHaveFocus();

    await user.tab();

    const preferencesItem = screen.getByRole('button', { name: '界面偏好' });
    expect(preferencesItem).toHaveFocus();

    await user.keyboard('{Enter}');

    const backButton = screen.getByRole('button', { name: '返回' });
    expect(backButton).toHaveFocus();
    expect(screen.getByRole('button', { name: '深色模式' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '关闭动画' })).toBeInTheDocument();
    expect(screen.getByLabelText('蓝色（默认）')).toBeInTheDocument();
    expect(screen.getByLabelText('缩放比例')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '登出' })).not.toBeInTheDocument();

    await user.keyboard('{Enter}');

    expect(screen.getByRole('button', { name: '界面偏好' })).toHaveFocus();
  });

  it('animates forward into the language submenu and backward to root when motion is enabled', async () => {
    const user = userEvent.setup();

    renderUserMenu();

    const trigger = screen.getByRole('button', { name: '用户菜单' });
    await user.click(trigger);

    const dropdown = document.getElementById(trigger.getAttribute('aria-controls') ?? '');
    expect(dropdown).toHaveAttribute('data-transition-direction', 'idle');

    await user.click(screen.getByRole('button', { name: /Language/i }));

    expect(dropdown).toHaveAttribute('data-transition-direction', 'forward');
    expect(dropdown?.querySelectorAll('.user-menu__panel-frame')).toHaveLength(2);
    expect(screen.getByRole('button', { name: '返回' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '返回' }));

    expect(dropdown).toHaveAttribute('data-transition-direction', 'backward');
    expect(dropdown?.querySelectorAll('.user-menu__panel-frame')).toHaveLength(2);
  });

  it('keeps a single divider during animated submenu transitions and uses an icon-only back button', async () => {
    const user = userEvent.setup();

    renderUserMenu();

    const trigger = screen.getByRole('button', { name: '用户菜单' });
    await user.click(trigger);

    const dropdown = document.getElementById(trigger.getAttribute('aria-controls') ?? '');
    expect(dropdown?.querySelectorAll('.user-menu__section-divider')).toHaveLength(1);

    await user.click(screen.getByRole('button', { name: /Language/i }));

    expect(dropdown?.querySelectorAll('.user-menu__section-divider')).toHaveLength(1);

    const backButton = screen.getByRole('button', { name: '返回' });
    expect(backButton).toBeInTheDocument();
    expect(screen.queryByText('返回')).not.toBeInTheDocument();
  });

  it('switches submenus immediately when motion is disabled', async () => {
    localStorage.setItem('agentlabkit-motion', 'false');
    const user = userEvent.setup();

    renderUserMenu();

    const trigger = screen.getByRole('button', { name: '用户菜单' });
    await user.click(trigger);

    const dropdown = document.getElementById(trigger.getAttribute('aria-controls') ?? '');

    await user.click(screen.getByRole('button', { name: /Language/i }));

    expect(dropdown).toHaveAttribute('data-transition-direction', 'idle');
    expect(dropdown?.querySelectorAll('.user-menu__panel-frame')).toHaveLength(1);
    expect(screen.getByRole('button', { name: '返回' })).toHaveFocus();
  });

  it('returns focus to the trigger when the root menu closes with Escape', async () => {
    const user = userEvent.setup();

    renderUserMenu();

    const trigger = screen.getByRole('button', { name: '用户菜单' });
    trigger.focus();

    await user.keyboard('{Enter}');
    expect(screen.getByRole('button', { name: /Language/i })).toHaveFocus();

    await user.keyboard('{Escape}');

    expect(screen.queryByRole('button', { name: /Language/i })).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it('closes the popover when tabbing forward out of the trigger and root panel subtree', async () => {
    const user = userEvent.setup();

    renderUserMenu(<button type="button">Outside action</button>);

    const trigger = screen.getByRole('button', { name: '用户菜单' });
    trigger.focus();

    await user.keyboard('{Enter}');
    expect(screen.getByRole('button', { name: /Language/i })).toHaveFocus();

    await user.tab();
    await user.tab();
    await user.tab();

    const outsideButton = screen.getByRole('button', { name: 'Outside action' });
    expect(outsideButton).toHaveFocus();
    expect(screen.queryByRole('button', { name: /Language/i })).not.toBeInTheDocument();
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
  });

  it('closes the popover when shift-tabbing backward out of the trigger and root panel subtree', async () => {
    const user = userEvent.setup();

    render(
      <>
        <button type="button">Before action</button>
        <ThemeProvider>
          <DocumentLanguageSync />
          <UserMenu displayName="Admin User" onLogout={vi.fn()} />
        </ThemeProvider>
      </>,
    );

    const trigger = screen.getByRole('button', { name: '用户菜单' });
    trigger.focus();

    await user.keyboard('{Enter}');
    expect(screen.getByRole('button', { name: /Language/i })).toHaveFocus();

    await user.tab({ shift: true });
    expect(trigger).toHaveFocus();
    expect(trigger).toHaveAttribute('aria-expanded', 'true');

    await user.tab({ shift: true });

    const beforeButton = screen.getByRole('button', { name: 'Before action' });
    expect(beforeButton).toHaveFocus();
    expect(screen.queryByRole('button', { name: /Language/i })).not.toBeInTheDocument();
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
  });

  it('returns focus to the trigger when a submenu closes with Escape', async () => {
    const user = userEvent.setup();

    renderUserMenu();

    const trigger = screen.getByRole('button', { name: '用户菜单' });
    trigger.focus();

    await user.keyboard('{Enter}');
    await user.keyboard('{Enter}');
    expect(screen.getByRole('button', { name: '返回' })).toHaveFocus();

    await user.keyboard('{Escape}');

    expect(screen.queryByRole('button', { name: '返回' })).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it('keeps focus on a focusable outside target when a submenu closes from an outside click', async () => {
    const user = userEvent.setup();

    renderUserMenu(<button type="button">Outside action</button>);

    const trigger = screen.getByRole('button', { name: '用户菜单' });
    trigger.focus();

    await user.keyboard('{Enter}');
    await user.tab();
    await user.keyboard('{Enter}');
    expect(screen.getByRole('button', { name: '返回' })).toHaveFocus();

    const outsideButton = screen.getByRole('button', { name: 'Outside action' });
    await user.click(outsideButton);

    expect(screen.queryByRole('button', { name: '返回' })).not.toBeInTheDocument();
    await waitFor(() => {
      expect(outsideButton).toHaveFocus();
    });
  });

  it('returns focus to the trigger when a submenu closes from an outside click on a non-focusable target', async () => {
    const user = userEvent.setup();

    renderUserMenu(<div data-testid="outside">outside</div>);

    const trigger = screen.getByRole('button', { name: '用户菜单' });
    trigger.focus();

    await user.keyboard('{Enter}');
    await user.tab();
    await user.keyboard('{Enter}');
    expect(screen.getByRole('button', { name: '返回' })).toHaveFocus();

    await user.click(screen.getByTestId('outside'));

    expect(screen.queryByRole('button', { name: '返回' })).not.toBeInTheDocument();
    await waitFor(() => {
      expect(trigger).toHaveFocus();
    });
  });

  it('keeps focus on a delegated outside control when a submenu closes from clicking its label', async () => {
    const user = userEvent.setup();

    renderUserMenu(
      <>
        <label htmlFor="outside-name">Outside name</label>
        <input id="outside-name" />
      </>,
    );

    const trigger = screen.getByRole('button', { name: '用户菜单' });
    trigger.focus();

    await user.keyboard('{Enter}');
    await user.tab();
    await user.keyboard('{Enter}');
    expect(screen.getByRole('button', { name: '返回' })).toHaveFocus();

    await user.click(screen.getByText('Outside name'));

    const outsideInput = screen.getByRole('textbox');
    expect(screen.queryByRole('button', { name: '返回' })).not.toBeInTheDocument();
    await waitFor(() => {
      expect(outsideInput).toHaveFocus();
    });
  });

  it('does not reopen the menu when locale change finishes after Escape closes the language submenu', async () => {
    const user = userEvent.setup();
    const deferred = createDeferred<Awaited<ReturnType<typeof i18n.changeLanguage>>>();
    const changeLanguageMock = vi
      .spyOn(i18n, 'changeLanguage')
      .mockImplementation(() => deferred.promise);

    renderUserMenu();

    const trigger = screen.getByRole('button', { name: '用户菜单' });
    trigger.focus();

    await user.keyboard('{Enter}');
    await user.keyboard('{Enter}');

    await user.click(screen.getByRole('button', { name: 'English' }));
    await user.keyboard('{Escape}');

    expect(screen.queryByRole('button', { name: '返回' })).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();

    deferred.resolve(i18n.t);
    await Promise.resolve();
    await new Promise((resolve) => window.setTimeout(resolve, 0));

    expect(screen.queryByRole('button', { name: /Language/i })).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();

    changeLanguageMock.mockRestore();
  });

  it('does not steal focus back when locale change finishes after an outside click closes the language submenu', async () => {
    const user = userEvent.setup();
    const deferred = createDeferred<Awaited<ReturnType<typeof i18n.changeLanguage>>>();
    const changeLanguageMock = vi
      .spyOn(i18n, 'changeLanguage')
      .mockImplementation(() => deferred.promise);

    renderUserMenu(<button type="button">Outside action</button>);

    const trigger = screen.getByRole('button', { name: '用户菜单' });
    trigger.focus();

    await user.keyboard('{Enter}');
    await user.keyboard('{Enter}');
    await user.click(screen.getByRole('button', { name: 'English' }));

    const outsideButton = screen.getByRole('button', { name: 'Outside action' });
    await user.click(outsideButton);

    expect(screen.queryByRole('button', { name: '返回' })).not.toBeInTheDocument();
    expect(outsideButton).toHaveFocus();

    deferred.resolve(i18n.t);
    await Promise.resolve();
    await new Promise((resolve) => window.setTimeout(resolve, 0));

    expect(screen.queryByRole('button', { name: /Language/i })).not.toBeInTheDocument();
    expect(outsideButton).toHaveFocus();

    changeLanguageMock.mockRestore();
  });
});
