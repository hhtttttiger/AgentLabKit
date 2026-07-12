import { useCallback, useEffect, useId, useRef, useState } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  KeyRound,
  Languages,
  LogOut,
  Moon,
  Palette,
  SlidersHorizontal,
  Sparkles,
  Sun,
  User,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAdminLocale } from '@/shared/i18n/useAdminLocale';
import { useTheme } from '../theme';
import { useMotion } from '../motion/useMotion';
import { AccentPicker } from './AccentPicker';
import { ChangePasswordDialog } from './ChangePasswordDialog';
import { LanguagePicker } from './LanguagePicker';
import { ProfileDialog } from './ProfileDialog';
import { ZoomSlider } from './ZoomSlider';
import './UserMenu.css';

interface UserMenuProps {
  displayName: string;
  onLogout: () => void;
}

type UserMenuView = 'root' | 'language' | 'preferences';
type RootFocusTarget = 'language' | 'preferences' | null;
type TriggerFocusRestoreMode = 'always' | 'if-needed' | 'never';
type UserMenuTransitionDirection = 'forward' | 'backward';

interface UserMenuTransitionState {
  from: UserMenuView;
  to: UserMenuView;
  direction: UserMenuTransitionDirection;
}

interface UserMenuViewRenderOptions {
  showSectionDivider?: boolean;
}

const SUBMENU_TRANSITION_MS = 180;

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

function shouldRestoreTriggerFocus(mode: TriggerFocusRestoreMode): boolean {
  if (mode === 'always') return true;
  if (mode === 'never') return false;

  const activeElement = document.activeElement;
  return !activeElement
    || activeElement === document.body
    || activeElement === document.documentElement
    || !document.contains(activeElement);
}

export function UserMenu({ displayName, onLogout }: UserMenuProps) {
  const [open, setOpen] = useState(false);
  const [view, setView] = useState<UserMenuView>('root');
  const [transition, setTransition] = useState<UserMenuTransitionState | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [changePasswordOpen, setChangePasswordOpen] = useState(false);
  const dropdownId = useId();
  const menuRef = useRef<HTMLDivElement>(null);
  const openRef = useRef(false);
  const viewRef = useRef<UserMenuView>('root');
  const menuStateVersionRef = useRef(0);
  const transitionTimerRef = useRef<number | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const languageItemRef = useRef<HTMLButtonElement>(null);
  const preferencesItemRef = useRef<HTMLButtonElement>(null);
  const backButtonRef = useRef<HTMLButtonElement>(null);
  const pendingRootFocusRef = useRef<RootFocusTarget>(null);
  const restoreTriggerFocusRef = useRef<TriggerFocusRestoreMode>('never');
  const { t } = useTranslation('common');
  const { locale } = useAdminLocale();
  const { resolvedTheme, toggleTheme } = useTheme();
  const { motionEnabled, toggleMotion } = useMotion();

  const isDark = resolvedTheme === 'dark';
  const initials = getInitials(displayName);

  const clearTransitionTimer = useCallback(() => {
    if (transitionTimerRef.current !== null) {
      window.clearTimeout(transitionTimerRef.current);
      transitionTimerRef.current = null;
    }
  }, []);

  const applyMenuState = useCallback((
    nextOpen: boolean,
    nextView: UserMenuView,
    transitionDirection?: UserMenuTransitionDirection,
  ) => {
    const previousOpen = openRef.current;
    const previousView = viewRef.current;

    menuStateVersionRef.current += 1;
    openRef.current = nextOpen;
    viewRef.current = nextView;
    setOpen(nextOpen);
    setView(nextView);

    if (!nextOpen || !previousOpen || !motionEnabled || !transitionDirection || previousView === nextView) {
      clearTransitionTimer();
      setTransition(null);
      return;
    }

    setTransition({
      from: previousView,
      to: nextView,
      direction: transitionDirection,
    });

    clearTransitionTimer();
    transitionTimerRef.current = window.setTimeout(() => {
      setTransition(null);
      transitionTimerRef.current = null;
    }, SUBMENU_TRANSITION_MS);
  }, [clearTransitionTimer, motionEnabled]);

  const close = useCallback(({ restoreTriggerFocus = 'never' }: { restoreTriggerFocus?: TriggerFocusRestoreMode } = {}) => {
    pendingRootFocusRef.current = null;
    restoreTriggerFocusRef.current = restoreTriggerFocus;
    applyMenuState(false, 'root');
  }, [applyMenuState]);

  const openRoot = useCallback((focusTarget: RootFocusTarget = null) => {
    pendingRootFocusRef.current = focusTarget;
    applyMenuState(true, 'root', viewRef.current === 'root' ? undefined : 'backward');
  }, [applyMenuState]);

  const openSubmenu = useCallback((nextView: Exclude<UserMenuView, 'root'>) => {
    pendingRootFocusRef.current = nextView;
    applyMenuState(true, nextView, 'forward');
  }, [applyMenuState]);

  useEffect(() => () => {
    clearTransitionTimer();
  }, [clearTransitionTimer]);

  useEffect(() => {
    if (!open) return;

    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        close({ restoreTriggerFocus: 'if-needed' });
      }
    }

    function handleFocusOutside(e: FocusEvent) {
      if (openRef.current && menuRef.current && !menuRef.current.contains(e.target as Node)) {
        close({ restoreTriggerFocus: 'never' });
      }
    }

    function handleEscape(e: KeyboardEvent) {
      if (e.key === 'Escape') close({ restoreTriggerFocus: 'always' });
    }

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('focusin', handleFocusOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('focusin', handleFocusOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [open, close]);

  useEffect(() => {
    if (open || restoreTriggerFocusRef.current === 'never') return;

    const restoreMode = restoreTriggerFocusRef.current;
    restoreTriggerFocusRef.current = 'never';
    const focusTimer = window.setTimeout(() => {
      if (shouldRestoreTriggerFocus(restoreMode)) {
        triggerRef.current?.focus();
      }
    }, 0);

    return () => {
      window.clearTimeout(focusTimer);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;

    if (view === 'language' || view === 'preferences') {
      backButtonRef.current?.focus();
      return;
    }

    const nextFocusTarget = pendingRootFocusRef.current === 'preferences'
      ? preferencesItemRef.current
      : languageItemRef.current;
    pendingRootFocusRef.current = null;
    nextFocusTarget?.focus();
  }, [open, view]);

  function renderSectionDivider() {
    return <div className="user-menu__section-divider" aria-hidden="true" />;
  }

  function renderSubmenuHeader(
    title: string,
    focusTarget: Exclude<RootFocusTarget, null>,
    showSectionDivider = true,
  ) {
    return (
      <>
        <div className="user-menu__submenu-header">
          <button
            ref={backButtonRef}
            type="button"
            className="user-menu__back"
            aria-label={t('userMenu.back')}
            title={t('userMenu.back')}
            onClick={() => openRoot(focusTarget)}
          >
            <ChevronLeft size={16} />
          </button>
          <span className="user-menu__submenu-title">{title}</span>
        </div>
        {showSectionDivider ? renderSectionDivider() : null}
      </>
    );
  }

  function renderRootView({ showSectionDivider = true }: UserMenuViewRenderOptions = {}) {
    return (
      <>
        <div className="user-menu__header">
          <div className="user-menu__avatar-sm">{initials}</div>
          <div className="user-menu__header-copy">
            <span className="user-menu__eyebrow">{t('userMenu.account')}</span>
            <span className="user-menu__name">{displayName}</span>
          </div>
        </div>
        {showSectionDivider ? renderSectionDivider() : null}

        <button
          ref={languageItemRef}
          type="button"
          className="user-menu__item user-menu__item--submenu"
          onClick={() => openSubmenu('language')}
        >
          <Languages size={16} />
          <span className="user-menu__item-label">{t('userMenu.language')}</span>
          <span className="user-menu__item-meta">{t(`userMenu.localeShort.${locale}`)}</span>
          <ChevronRight size={16} className="user-menu__item-chevron" />
        </button>

        <button
          ref={preferencesItemRef}
          type="button"
          className="user-menu__item user-menu__item--submenu"
          onClick={() => openSubmenu('preferences')}
        >
          <SlidersHorizontal size={16} />
          <span className="user-menu__item-label">{t('userMenu.preferences')}</span>
          <ChevronRight size={16} className="user-menu__item-chevron" />
        </button>

        <div className="user-menu__divider" />

        <button
          type="button"
          className="user-menu__item"
          onClick={() => {
            close();
            setProfileOpen(true);
          }}
        >
          <User size={16} />
          <span className="user-menu__item-label">{t('userMenu.profile')}</span>
        </button>

        <button
          type="button"
          className="user-menu__item"
          onClick={() => {
            close();
            setChangePasswordOpen(true);
          }}
        >
          <KeyRound size={16} />
          <span className="user-menu__item-label">{t('userMenu.changePassword')}</span>
        </button>

        <div className="user-menu__divider" />

        <button
          type="button"
          className="user-menu__item user-menu__item--danger"
          onClick={() => {
            onLogout();
            close();
          }}
        >
          <LogOut size={16} />
          <span className="user-menu__item-label">{t('userMenu.logout')}</span>
        </button>
      </>
    );
  }

  function renderLanguageView({ showSectionDivider = true }: UserMenuViewRenderOptions = {}) {
    const menuStateVersion = menuStateVersionRef.current;

    return (
      <div className="user-menu__panel">
        {renderSubmenuHeader(t('userMenu.languageTitle'), 'language', showSectionDivider)}
        <LanguagePicker
          className="user-menu__language-picker"
          shouldNotifySelection={() => (
            openRef.current
            && viewRef.current === 'language'
            && menuStateVersionRef.current === menuStateVersion
          )}
          onSelect={() => openRoot('language')}
        />
      </div>
    );
  }

  function renderPreferencesView({ showSectionDivider = true }: UserMenuViewRenderOptions = {}) {
    return (
      <div className="user-menu__panel">
        {renderSubmenuHeader(t('userMenu.preferencesTitle'), 'preferences', showSectionDivider)}

        <button
          type="button"
          className="user-menu__item"
          onClick={() => { toggleTheme(); }}
        >
          {isDark ? <Sun size={16} /> : <Moon size={16} />}
          <span className="user-menu__item-label">
            {isDark ? t('preferences.theme.light') : t('preferences.theme.dark')}
          </span>
        </button>

        <button
          type="button"
          className="user-menu__item"
          onClick={() => { toggleMotion(); }}
        >
          <Sparkles size={16} className={motionEnabled ? 'text-primary' : 'opacity-40'} />
          <span className="user-menu__item-label">
            {motionEnabled ? t('preferences.motion.disable') : t('preferences.motion.enable')}
          </span>
        </button>

        <div className="user-menu__group" aria-label={t('preferences.accent')}>
          <div className="user-menu__group-header">
            <Palette size={16} />
            <span>{t('preferences.accent')}</span>
          </div>
          <AccentPicker />
        </div>

        <div className="user-menu__group user-menu__group--zoom">
          <span className="user-menu__group-label">{t('preferences.zoom')}</span>
          <ZoomSlider />
        </div>
      </div>
    );
  }

  function renderView(targetView: UserMenuView, options?: UserMenuViewRenderOptions) {
    if (targetView === 'root') return renderRootView(options);
    if (targetView === 'language') return renderLanguageView(options);
    return renderPreferencesView(options);
  }

  return (
    <>
      <div className="user-menu" ref={menuRef}>
        <button
          ref={triggerRef}
          type="button"
          className="user-menu__trigger"
          onClick={() => {
            if (open) {
              close();
            } else {
              openRoot();
            }
          }}
          aria-label={t('userMenu.ariaLabel')}
          aria-expanded={open}
          aria-controls={open ? dropdownId : undefined}
        >
          {initials}
        </button>

        {open && (
          <div
            id={dropdownId}
            className="user-menu__dropdown"
            data-current-view={view}
            data-transition-direction={transition?.direction ?? 'idle'}
          >
            <div className="user-menu__viewport">
              {transition ? (
                <>
                  <div
                    className="user-menu__panel-frame user-menu__panel-frame--outgoing"
                    aria-hidden="true"
                  >
                    {renderView(transition.from, { showSectionDivider: false })}
                  </div>
                  <div className="user-menu__panel-frame user-menu__panel-frame--incoming">
                    {renderView(transition.to)}
                  </div>
                </>
              ) : (
                <div className="user-menu__panel-frame user-menu__panel-frame--current">
                  {renderView(view)}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <ProfileDialog open={profileOpen} onClose={() => setProfileOpen(false)} />
      <ChangePasswordDialog open={changePasswordOpen} onClose={() => setChangePasswordOpen(false)} />
    </>
  );
}
