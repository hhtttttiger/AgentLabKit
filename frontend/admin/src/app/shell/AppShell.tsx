import { useState } from 'react';
import { useLocation, useNavigate, useOutlet } from 'react-router-dom';
import { AppSidebar } from './AppSidebar';
import { appModules } from '../modules';
import { useAuth } from '@/shared/auth';
import { ErrorBoundary } from '@/shared/error/ErrorBoundary';
import { useMediaQuery } from '@/shared/hooks/useMediaQuery';
import './AppShell.css';

const SIDEBAR_COLLAPSED_KEY = 'agentlabkit-sidebar-collapsed';
const SIDEBAR_FORCE_EXPANDED_KEY = 'agentlabkit-sidebar-force-expanded';

function loadUserCollapsed(): boolean {
  return window.localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true';
}

function loadForceExpanded(): boolean {
  return window.localStorage.getItem(SIDEBAR_FORCE_EXPANDED_KEY) === 'true';
}

export function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const outlet = useOutlet();
  const { user, logout } = useAuth();
  const [userCollapsed, setUserCollapsed] = useState(loadUserCollapsed);
  const [forceExpanded, setForceExpanded] = useState(loadForceExpanded);
  const isSmallScreen = useMediaQuery('(max-width: 1400px)');
  const collapsed = forceExpanded ? false : (userCollapsed || isSmallScreen);

  const currentModule = appModules.find((item) => location.pathname.startsWith(item.basePath));

  function handleLogout() {
    logout();
    navigate('/login', { replace: true });
  }

  function toggleCollapsed() {
    if (collapsed) {
      setUserCollapsed(false);
      window.localStorage.setItem(SIDEBAR_COLLAPSED_KEY, 'false');
      if (isSmallScreen) {
        setForceExpanded(true);
        window.localStorage.setItem(SIDEBAR_FORCE_EXPANDED_KEY, 'true');
      }
    } else {
      setUserCollapsed(true);
      window.localStorage.setItem(SIDEBAR_COLLAPSED_KEY, 'true');
      setForceExpanded(false);
      window.localStorage.removeItem(SIDEBAR_FORCE_EXPANDED_KEY);
    }
  }

  const displayName = user?.userName ?? `User #${user?.userId ?? ''}`;

  return (
    <div
      className={`admin-shell${collapsed ? ' admin-shell--collapsed' : ''}`}
    >
      <AppSidebar
        currentModuleKey={currentModule?.key}
        collapsed={collapsed}
        onToggleCollapse={toggleCollapsed}
        displayName={displayName}
        onLogout={handleLogout}
      />
      <main className="admin-shell__content">
        <div className="admin-shell__panel">
          <ErrorBoundary>
            {outlet}
          </ErrorBoundary>
        </div>
      </main>
    </div>
  );
}
