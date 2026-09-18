import { NavLink } from 'react-router-dom';
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { UserMenu } from '@/shared/ui/UserMenu';
import { getModulesByGroup, type ModuleGroup } from '../modules';
import type { ModuleKey } from '../modules';
import { isLocalDesktopMode } from '@/shared/runtime/config';
import './AppSidebar.css';

interface AppSidebarProps {
  currentModuleKey?: string;
  collapsed: boolean;
  onToggleCollapse: () => void;
  displayName: string;
  onLogout: () => void;
}

const NAV_LABELS: Record<ModuleKey, string> = {
  home: 'desktop:nav.home', sessions: 'desktop:nav.sessions', runs: 'desktop:nav.runs', datasets: 'desktop:nav.datasets', evaluation: 'desktop:nav.evaluations', 'knowledge-base': 'desktop:nav.knowledge', settings: 'desktop:nav.settings',
} as const;

export function AppSidebar({ currentModuleKey, collapsed, onToggleCollapse, displayName, onLogout }: AppSidebarProps) {
  const { t } = useTranslation(['common', 'desktop']);
  const groupedModules = getModulesByGroup();

  // Render groups in defined order
  const groupOrder: ModuleGroup[] = ['build', 'run', 'improve', 'platform'];

  return (
    <aside className={`admin-sidebar ${collapsed ? 'admin-sidebar--collapsed' : ''}`}>
      <div className="admin-sidebar__brand">
        <div className="admin-sidebar__brand-mark">A</div>
        <div className="admin-sidebar__brand-text">
          <div className="admin-sidebar__brand-title">AgentLab</div>
          <div className="admin-sidebar__brand-subtitle">{t('desktop:brandSubtitle')}</div>
        </div>
      </div>

      <nav
        className="admin-sidebar__nav"
        aria-label={t('nav.ariaLabel')}
        style={{ minHeight: 0, overflowY: 'auto' }}
      >
        {groupOrder.map((group) => {
          const modules = groupedModules.get(group);
          if (!modules || modules.length === 0) return null;

          return (
            <div key={group} className="admin-sidebar__group">
              {!collapsed && <div className="admin-sidebar__group-label">{t(`desktop:groups.${group === 'build' ? 'workspace' : group === 'run' ? 'work' : group === 'improve' ? 'engineering' : 'context'}`)}</div>}
              {modules.filter((module) => module.key !== 'settings' || isLocalDesktopMode()).map((module) => {
                const Icon = module.icon;
                const label = t(NAV_LABELS[module.key]);
                return (
                  <NavLink
                    key={module.key}
                    to={module.basePath}
                    title={collapsed ? label : undefined}
                    className={`admin-sidebar__link ${currentModuleKey === module.key ? 'admin-sidebar__link--active' : ''}`}
                  >
                    <Icon size={18} />
                    <span className="admin-sidebar__link-label">{label}</span>
                  </NavLink>
                );
              })}
            </div>
          );
        })}
      </nav>

      <NavLink className="sr-only" to="/playground">Playground</NavLink>

      <div className="admin-sidebar__footer">
        <div className="admin-sidebar__footer-left">
          <UserMenu displayName={displayName} onLogout={onLogout} />
          {!collapsed && (
            <span className="admin-sidebar__footer-user-name">{displayName}</span>
          )}
        </div>
        <button
          type="button"
          className="admin-sidebar__toggle"
          onClick={onToggleCollapse}
          title={collapsed ? t('nav.expand') : t('nav.collapse')}
          aria-label={collapsed ? t('nav.expand') : t('nav.collapse')}
        >
          {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
        </button>
      </div>
    </aside>
  );
}
