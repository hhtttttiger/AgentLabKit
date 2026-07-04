# User Menu and Login Preferences Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the authenticated user menu into a language-first two-level menu and add a compact login-page preferences bar for language, accent, and theme before sign-in.

**Architecture:** Keep the existing `UserMenu`, `LoginPage`, and shared picker components, but reshape them into clearer interaction states instead of introducing a full settings page. `UserMenu` becomes a tiny view-state machine (`root | language | preferences`), while the login page upgrades its existing footer `ThemeToggle` into a reusable pre-auth preferences bar that reuses the locale and theme infrastructure already in the template.

**Tech Stack:** React 19, TypeScript, react-i18next, lucide-react, Tailwind utility classes + `src/styles/index.css`, Vitest + Testing Library.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/shared/ui/UserMenu.tsx` | **Modify** | Replace flat dropdown with root/language/preferences views |
| `src/shared/ui/UserMenu.test.tsx` | **Modify** | Verify root menu structure, language submenu, preferences submenu, and logout |
| `src/shared/ui/LanguagePicker.tsx` | **Modify** | Support reuse in submenus/footer with `className` and optional `onSelect` callback |
| `src/shared/ui/AccentPicker.tsx` | **Modify** | Localize option labels and support compact footer usage |
| `src/shared/ui/ThemeToggle.tsx` | **Modify** | Add inline placement variant for login footer |
| `src/app/pages/LoginPage.tsx` | **Modify** | Replace lone bottom theme button with login preferences bar |
| `src/app/pages/LoginPage.test.tsx` | **Modify** | Verify login footer renders and updates locale/accent/theme state |
| `src/shared/i18n/resources.ts` | **Modify** | Add user-menu/login copy and localized accent labels |
| `src/styles/index.css` | **Modify** | Add submenu styles and login footer preference bar styles |

---

## Task 1: Reshape `UserMenu` into root / language / preferences views

**Files:**
- Modify: `src/shared/ui/UserMenu.tsx`
- Modify: `src/shared/ui/UserMenu.test.tsx`
- Modify: `src/shared/ui/LanguagePicker.tsx`
- Modify: `src/shared/i18n/resources.ts`
- Modify: `src/styles/index.css`

- [ ] **Step 1.1 — Write the failing `UserMenu` test**

Replace `src/shared/ui/UserMenu.test.tsx` with:

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createStorageMock } from '@/shared/test/storage';

describe('UserMenu navigation', () => {
  beforeEach(() => {
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
  });

  it('shows a compact first-level menu and drills into language/preferences panels', async () => {
    const { ThemeProvider } = await import('@/shared/theme');
    const { DocumentLanguageSync } = await import('@/shared/i18n/DocumentLanguageSync');
    const { UserMenu } = await import('./UserMenu');
    const onLogout = vi.fn();
    const user = userEvent.setup();

    render(
      <ThemeProvider>
        <DocumentLanguageSync />
        <UserMenu displayName="Admin User" onLogout={onLogout} />
      </ThemeProvider>,
    );

    await user.click(screen.getByRole('button', { name: '用户菜单' }));

    expect(screen.getByText('Admin User')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Language' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '界面偏好' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '登出' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'English' })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Language' }));
    expect(screen.getByRole('button', { name: 'English' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '简体中文' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'English' }));
    await waitFor(() => {
      expect(document.documentElement.lang).toBe('en-US');
      expect(localStorage.getItem('ai-admin-locale')).toBe('en-US');
    });

    await user.click(screen.getByRole('button', { name: 'User menu' }));
    await user.click(screen.getByRole('button', { name: 'Interface preferences' }));

    expect(screen.getByRole('button', { name: 'Enable motion' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Switch to dark mode' })).toBeInTheDocument();
    expect(screen.getByRole('group', { name: 'Accent color' })).toBeInTheDocument();
  });
});
```

- [ ] **Step 1.2 — Run the test to confirm FAIL**

Run:

```bash
cd <project-root>/templates/react-ts/ai-admin
npx vitest run src/shared/ui/UserMenu.test.tsx
```

Expected: FAIL because the current first-level menu still renders `LanguagePicker`, `AccentPicker`, and `ZoomSlider` inline instead of root/language/preferences views.

- [ ] **Step 1.3 — Add the missing copy and picker hook**

Update `src/shared/i18n/resources.ts` with these exact additions inside both locales:

```ts
userMenu: {
  ariaLabel: '用户菜单',
  logout: '登出',
  languageEntry: 'Language',
  preferencesEntry: '界面偏好',
  back: '返回',
}
```

```ts
userMenu: {
  ariaLabel: 'User menu',
  logout: 'Log out',
  languageEntry: 'Language',
  preferencesEntry: 'Interface preferences',
  back: 'Back',
}
```

Then update `src/shared/ui/LanguagePicker.tsx` to make it reusable from the user-menu language panel:

```tsx
import { useTranslation } from 'react-i18next';
import { useAdminLocale } from '@/shared/i18n/useAdminLocale';

interface LanguagePickerProps {
  className?: string;
  onSelect?: () => void;
}

export function LanguagePicker({ className, onSelect }: LanguagePickerProps) {
  const { t } = useTranslation('common');
  const { locale, setLocale, supportedLocales } = useAdminLocale();

  return (
    <div
      className={['language-picker', className].filter(Boolean).join(' ')}
      role="group"
      aria-label={t('preferences.language.label')}
    >
      {supportedLocales.map((value) => {
        const active = value === locale;
        return (
          <button
            key={value}
            type="button"
            className={`language-picker__option${active ? ' language-picker__option--active' : ''}`}
            aria-pressed={active}
            onClick={async () => {
              await setLocale(value);
              onSelect?.();
            }}
          >
            {t(`preferences.language.options.${value}`)}
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 1.4 — Replace `UserMenu.tsx` with the view-state version**

Replace `src/shared/ui/UserMenu.tsx` with:

```tsx
import { useCallback, useEffect, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, Languages, LogOut, Moon, Palette, Sparkles, Sun } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAdminLocale } from '@/shared/i18n/useAdminLocale';
import { useTheme } from '../theme';
import { useMotion } from '../motion/useMotion';
import { AccentPicker } from './AccentPicker';
import { LanguagePicker } from './LanguagePicker';
import { ZoomSlider } from './ZoomSlider';

interface UserMenuProps {
  displayName: string;
  onLogout: () => void;
}

type UserMenuView = 'root' | 'language' | 'preferences';

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

export function UserMenu({ displayName, onLogout }: UserMenuProps) {
  const [open, setOpen] = useState(false);
  const [view, setView] = useState<UserMenuView>('root');
  const menuRef = useRef<HTMLDivElement>(null);
  const { t } = useTranslation('common');
  const { locale } = useAdminLocale();
  const { resolvedTheme, toggleTheme } = useTheme();
  const { motionEnabled, toggleMotion } = useMotion();

  const isDark = resolvedTheme === 'dark';
  const initials = getInitials(displayName);

  const close = useCallback(() => {
    setOpen(false);
    setView('root');
  }, []);

  useEffect(() => {
    if (!open) {
      setView('root');
      return;
    }

    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        close();
      }
    }
    function handleEscape(e: KeyboardEvent) {
      if (e.key === 'Escape') close();
    }

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [open, close]);

  return (
    <div className="user-menu" ref={menuRef}>
      <button
        type="button"
        className="user-menu__trigger"
        onClick={() => setOpen((prev) => !prev)}
        aria-label={t('userMenu.ariaLabel')}
        aria-expanded={open}
        aria-haspopup="menu"
      >
        {initials}
      </button>

      {open && (
        <div className="user-menu__dropdown" role="menu">
          <div className="user-menu__header">
            <div className="user-menu__avatar-sm">{initials}</div>
            <span className="user-menu__name">{displayName}</span>
          </div>

          {view === 'root' && (
            <>
              <button type="button" className="user-menu__item user-menu__item--submenu" role="menuitem">
                <span className="user-menu__item-main">
                  <Languages size={16} />
                  <span>{t('userMenu.languageEntry')}</span>
                </span>
                <span className="user-menu__meta">
                  {t(`preferences.language.options.${locale}`)}
                  <ChevronRight size={14} />
                </span>
              </button>

              <button
                type="button"
                className="user-menu__item user-menu__item--submenu"
                role="menuitem"
                onClick={() => setView('preferences')}
              >
                <span className="user-menu__item-main">
                  <Palette size={16} />
                  <span>{t('userMenu.preferencesEntry')}</span>
                </span>
                <ChevronRight size={14} />
              </button>

              <button
                type="button"
                className="user-menu__item user-menu__item--danger"
                role="menuitem"
                onClick={() => {
                  onLogout();
                  close();
                }}
              >
                <LogOut size={16} />
                <span>{t('userMenu.logout')}</span>
              </button>
            </>
          )}

          {view === 'language' && (
            <>
              <button type="button" className="user-menu__back" onClick={() => setView('root')}>
                <ChevronLeft size={14} />
                <span>{t('userMenu.back')}</span>
              </button>
              <div className="user-menu__panel">
                <LanguagePicker className="language-picker--menu" onSelect={close} />
              </div>
            </>
          )}

          {view === 'preferences' && (
            <>
              <button type="button" className="user-menu__back" onClick={() => setView('root')}>
                <ChevronLeft size={14} />
                <span>{t('userMenu.back')}</span>
              </button>

              <div className="user-menu__panel">
                <button type="button" className="user-menu__item" onClick={toggleTheme}>
                  {isDark ? <Sun size={16} /> : <Moon size={16} />}
                  <span>{isDark ? t('preferences.theme.light') : t('preferences.theme.dark')}</span>
                </button>

                <button type="button" className="user-menu__item" onClick={toggleMotion}>
                  <Sparkles size={16} className={motionEnabled ? 'text-primary' : 'opacity-40'} />
                  <span>{motionEnabled ? t('preferences.motion.disable') : t('preferences.motion.enable')}</span>
                </button>

                <div className="user-menu__section">
                  <div className="user-menu__section-label">{t('preferences.accent')}</div>
                  <AccentPicker />
                </div>

                <div className="user-menu__zoom-section">
                  <ZoomSlider />
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
```

Immediately fix the root language button in that file so it actually navigates into the language panel:

```tsx
<button
  type="button"
  className="user-menu__item user-menu__item--submenu"
  role="menuitem"
  onClick={() => setView('language')}
>
```

And add the supporting styles to `src/styles/index.css` right after the existing `.user-menu__item` rules:

```css
.user-menu__item-main {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.user-menu__item--submenu {
  justify-content: space-between;
}

.user-menu__meta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: rgb(var(--color-text-tertiary));
  font-size: 12px;
}

.user-menu__back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 4px 6px 8px;
  border: none;
  background: transparent;
  color: rgb(var(--color-text-secondary));
  font-size: 12px;
}

.user-menu__panel {
  display: grid;
  gap: 6px;
}

.user-menu__section {
  display: grid;
  gap: 8px;
  padding: 10px 12px;
}

.user-menu__section-label {
  font-size: 12px;
  color: rgb(var(--color-text-tertiary));
}

.language-picker--menu {
  justify-content: flex-start;
  margin-left: 0;
  padding: 4px 12px 10px;
}
```

- [ ] **Step 1.5 — Run the test to confirm PASS**

Run:

```bash
cd <project-root>/templates/react-ts/ai-admin
npx vitest run src/shared/ui/UserMenu.test.tsx
```

Expected: PASS with the first-level menu reduced to compact actions and the test navigating through both secondary panels successfully.

- [ ] **Step 1.6 — Commit**

Run:

```bash
cd <project-root>
git add \
  templates/react-ts/ai-admin/src/shared/ui/UserMenu.tsx \
  templates/react-ts/ai-admin/src/shared/ui/UserMenu.test.tsx \
  templates/react-ts/ai-admin/src/shared/ui/LanguagePicker.tsx \
  templates/react-ts/ai-admin/src/shared/i18n/resources.ts \
  templates/react-ts/ai-admin/src/styles/index.css
git commit -m "feat(ai-admin): split user menu into layered preferences"
```

---

## Task 2: Add the login-page preferences bar

**Files:**
- Modify: `src/app/pages/LoginPage.tsx`
- Modify: `src/app/pages/LoginPage.test.tsx`
- Modify: `src/shared/ui/AccentPicker.tsx`
- Modify: `src/shared/ui/ThemeToggle.tsx`
- Modify: `src/shared/i18n/resources.ts`
- Modify: `src/styles/index.css`

- [ ] **Step 2.1 — Write the failing login-page test**

Replace `src/app/pages/LoginPage.test.tsx` with:

```tsx
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

describe('LoginPage preferences footer', () => {
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
    document.documentElement.lang = 'en-US';
    document.documentElement.dataset.locale = 'en-US';
    document.documentElement.removeAttribute('data-accent');
    await i18n.changeLanguage('en-US');
  });

  it('renders a compact footer bar and persists locale/accent changes', async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <ThemeProvider>
          <DocumentLanguageSync />
          <LoginPage />
        </ThemeProvider>
      </MemoryRouter>,
    );

    expect(screen.getByRole('group', { name: 'Sign-in preferences' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'English' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Violet' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '简体中文' }));
    await waitFor(() => {
      expect(document.documentElement.lang).toBe('zh-CN');
      expect(localStorage.getItem('ai-admin-locale')).toBe('zh-CN');
      expect(screen.getByLabelText('用户名')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: '紫色' }));
    expect(document.documentElement.dataset.accent).toBe('violet');
    expect(localStorage.getItem('ai-admin-accent')).toBe('violet');
  });
});
```

- [ ] **Step 2.2 — Run the test to confirm FAIL**

Run:

```bash
cd <project-root>/templates/react-ts/ai-admin
npx vitest run src/app/pages/LoginPage.test.tsx
```

Expected: FAIL because the current login page still renders only a lone `ThemeToggle`, and `AccentPicker` labels are not localized for English.

- [ ] **Step 2.3 — Localize accent labels and add login-footer copy**

Update `src/shared/i18n/resources.ts` with the following additions:

```ts
preferences: {
  accent: '主题色',
  accentOptions: {
    blue: '蓝色（默认）',
    violet: '紫色',
    emerald: '绿色',
    rose: '玫瑰红',
    amber: '琥珀',
  },
}
```

```ts
preferences: {
  accent: 'Accent color',
  accentOptions: {
    blue: 'Blue (default)',
    violet: 'Violet',
    emerald: 'Emerald',
    rose: 'Rose',
    amber: 'Amber',
  },
}
```

```ts
login: {
  title: 'AI Admin',
  username: '用户名',
  usernamePlaceholder: '请输入用户名',
  password: '密码',
  passwordPlaceholder: '请输入密码',
  submit: '登录',
  submitting: '登录中…',
  errorFallback: '登录失败，请检查账号密码。',
  preferencesAriaLabel: '登录偏好',
}
```

```ts
login: {
  title: 'AI Admin',
  username: 'Username',
  usernamePlaceholder: 'Enter username',
  password: 'Password',
  passwordPlaceholder: 'Enter password',
  submit: 'Log in',
  submitting: 'Signing in…',
  errorFallback: 'Sign-in failed. Check your username and password.',
  preferencesAriaLabel: 'Sign-in preferences',
}
```

Then replace `src/shared/ui/AccentPicker.tsx` with:

```tsx
import { useTranslation } from 'react-i18next';
import type { AccentColor } from '../theme';
import { useTheme } from '../theme';

interface AccentOption {
  value: AccentColor;
  labelKey: string;
  color: string;
}

interface AccentPickerProps {
  className?: string;
}

const ACCENT_OPTIONS: AccentOption[] = [
  { value: 'blue', labelKey: 'preferences.accentOptions.blue', color: '#3b82f6' },
  { value: 'violet', labelKey: 'preferences.accentOptions.violet', color: '#8b5cf6' },
  { value: 'emerald', labelKey: 'preferences.accentOptions.emerald', color: '#10b981' },
  { value: 'rose', labelKey: 'preferences.accentOptions.rose', color: '#f43f5e' },
  { value: 'amber', labelKey: 'preferences.accentOptions.amber', color: '#f59e0b' },
];

export function AccentPicker({ className }: AccentPickerProps) {
  const { t } = useTranslation('common');
  const { accent, setAccent } = useTheme();

  return (
    <div className={['accent-picker', className].filter(Boolean).join(' ')} role="group" aria-label={t('preferences.accent')}>
      {ACCENT_OPTIONS.map((opt) => {
        const label = t(opt.labelKey);
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
```

- [ ] **Step 2.4 — Implement the login footer and inline theme style**

Update `src/shared/ui/ThemeToggle.tsx`:

```tsx
import { Moon, Sun } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../theme';

export function ThemeToggle({ placement = 'header' }: { placement?: 'sidebar' | 'header' | 'inline' }) {
  const { t } = useTranslation('common');
  const { resolvedTheme, toggleTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';
  const Icon = isDark ? Sun : Moon;
  const label = isDark ? t('themeToggle.toLight') : t('themeToggle.toDark');

  const className =
    placement === 'sidebar'
      ? 'theme-toggle theme-toggle--sidebar'
      : placement === 'inline'
        ? 'theme-toggle theme-toggle--inline'
        : 'theme-toggle theme-toggle--header';

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={label}
      title={label}
      className={className}
    >
      <Icon size={18} />
    </button>
  );
}
```

Update `src/app/pages/LoginPage.tsx`:

```tsx
import { type FormEvent, useState } from 'react';
import { Palette, Languages } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Navigate } from 'react-router-dom';
import { useAuth } from '@/shared/auth';
import { getErrorMessage } from '@/shared/api/errors';
import { Button } from '@/shared/ui/Button';
import { TextField } from '@/shared/ui/FormFields';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { ThemeToggle } from '@/shared/ui/ThemeToggle';
import { LanguagePicker } from '@/shared/ui/LanguagePicker';
import { AccentPicker } from '@/shared/ui/AccentPicker';

export function LoginPage() {
  const { t } = useTranslation('common');
  const { isAuthenticated, login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (isAuthenticated) {
    return <Navigate replace to="/" />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login(username, password);
    } catch (err) {
      setError(getErrorMessage(err, t('login.errorFallback')));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-aurora relative flex min-h-full items-center justify-center overflow-hidden p-6">
      <div
        className="login-aurora__blob w-[60vmax] h-[60vmax] -top-[20%] -left-[10%] bg-primary/30 dark:bg-primary/20"
        style={{ animation: 'aurora-1 20s ease-in-out infinite' }}
      />
      <div
        className="login-aurora__blob w-[50vmax] h-[50vmax] top-[30%] -right-[15%] bg-primary-subtle/45 dark:bg-primary-subtle/25"
        style={{ animation: 'aurora-2 24s ease-in-out infinite' }}
      />
      <div
        className="login-aurora__blob w-[45vmax] h-[45vmax] -bottom-[10%] left-[20%] bg-primary-hover/25 dark:bg-primary-hover/15"
        style={{ animation: 'aurora-3 18s ease-in-out infinite' }}
      />

      <div className="relative w-full max-w-[400px] rounded-3xl border border-white/20 bg-white/40 px-8 pt-10 pb-8 shadow-lg backdrop-blur-xl dark:border-white/10 dark:bg-white/10 animate-card-enter">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 inline-flex h-12 w-12 items-center justify-center rounded-[14px] bg-gradient-to-br from-primary to-primary-hover text-lg font-bold text-text-inverse shadow-[0_2px_8px_rgb(var(--color-primary)/0.25)] animate-brand-pulse">
            AI
          </div>
          <h1 className="m-0 text-[22px] font-bold text-text">{t('login.title')}</h1>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          {error && <InlineMessage tone="error">{error}</InlineMessage>}

          <TextField
            label={t('login.username')}
            placeholder={t('login.usernamePlaceholder')}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            autoFocus
            required
          />

          <TextField
            label={t('login.password')}
            type="password"
            placeholder={t('login.passwordPlaceholder')}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />

          <Button type="submit" variant="primary" className="w-full" disabled={loading}>
            {loading ? t('login.submitting') : t('login.submit')}
          </Button>
        </form>

        <div className="login-preferences" role="group" aria-label={t('login.preferencesAriaLabel')}>
          <div className="login-preferences__group">
            <span className="login-preferences__label">
              <Languages size={14} />
              <span>Language</span>
            </span>
            <LanguagePicker className="language-picker--compact" />
          </div>

          <div className="login-preferences__group">
            <span className="login-preferences__label">
              <Palette size={14} />
              <span>{t('preferences.accent')}</span>
            </span>
            <AccentPicker className="accent-picker--compact" />
          </div>

          <ThemeToggle placement="inline" />
        </div>
      </div>
    </div>
  );
}
```

Append these rules to `src/styles/index.css` after the existing `language-picker` / `accent-picker` styles:

```css
.language-picker--compact {
  margin-left: 0;
  padding-left: 0;
  flex-wrap: wrap;
}

.accent-picker--compact {
  gap: 6px;
}

.theme-toggle--inline {
  width: 32px;
  height: 32px;
  border: 1px solid rgb(var(--color-border-default) / 0.65);
  border-radius: 999px;
  background: transparent;
  color: rgb(var(--color-text-secondary));
}

.login-preferences {
  display: grid;
  gap: 12px;
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid rgb(var(--color-border-subtle));
}

.login-preferences__group {
  display: grid;
  gap: 8px;
}

.login-preferences__label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: rgb(var(--color-text-tertiary));
}
```

- [ ] **Step 2.5 — Run the login test to confirm PASS**

Run:

```bash
cd <project-root>/templates/react-ts/ai-admin
npx vitest run src/app/pages/LoginPage.test.tsx
```

Expected: PASS with the login footer rendering localized controls and persisting both locale and accent changes.

- [ ] **Step 2.6 — Commit**

Run:

```bash
cd <project-root>
git add \
  templates/react-ts/ai-admin/src/app/pages/LoginPage.tsx \
  templates/react-ts/ai-admin/src/app/pages/LoginPage.test.tsx \
  templates/react-ts/ai-admin/src/shared/ui/AccentPicker.tsx \
  templates/react-ts/ai-admin/src/shared/ui/ThemeToggle.tsx \
  templates/react-ts/ai-admin/src/shared/i18n/resources.ts \
  templates/react-ts/ai-admin/src/styles/index.css
git commit -m "feat(ai-admin): add login page preferences bar"
```

---

## Task 3: Final verification sweep

**Files:**
- Verify only: `src/shared/ui/UserMenu.tsx`
- Verify only: `src/app/pages/LoginPage.tsx`
- Verify only: `src/shared/i18n/resources.ts`
- Verify only: `src/styles/index.css`

- [ ] **Step 3.1 — Re-run the focused tests together**

Run:

```bash
cd <project-root>/templates/react-ts/ai-admin
npx vitest run src/shared/ui/UserMenu.test.tsx src/app/pages/LoginPage.test.tsx
```

Expected: PASS with both new interaction surfaces covered.

- [ ] **Step 3.2 — Run repository verification**

Run:

```bash
cd <project-root>/templates/react-ts/ai-admin
npm run check
npm run test
npm run build
```

Expected:

```text
check: no TypeScript errors
test: all tests passed
build: vite build completes successfully
```

- [ ] **Step 3.3 — Confirm clean working tree**

Run:

```bash
cd <project-root>
git --no-pager status --short
```

Expected: only the plan/spec commits already created earlier, with no unintended unstaged changes left after verification.
