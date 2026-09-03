import { NavLink } from 'react-router-dom';
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { UserMenu } from '@/shared/ui/UserMenu';
import { getModulesByGroup, type ModuleGroup } from '../modules';
import type { ModuleKey } from '../modules';
import './AppSidebar.css';

interface AppSidebarProps {
  currentModuleKey?: string;
  collapsed: boolean;
  onToggleCollapse: () => void;
  displayName: string;
  onLogout: () => void;
}

const NAV_LABEL_KEYS: Record<ModuleKey, string> = {
  'ai-chat': 'nav.playground',
  'agent-management': 'nav.agents',
  'model-management': 'nav.models',
  glossary: 'nav.glossary',
  'knowledge-base': 'nav.knowledge',
  'model-monitoring': 'nav.monitoring',
  'cost-analysis': 'nav.cost',
  observability: 'nav.traces',
  memory: 'nav.memory',
  evaluation: 'nav.evaluation',
  'user-management': 'nav.users',
  runs: 'nav.runs',
  capabilities: 'nav.capabilities',
} as const;

const GROUP_LABEL_KEYS: Record<ModuleGroup, string> = {
  build: 'nav.group.build',
  run: 'nav.group.run',
  improve: 'nav.group.improve',
  platform: 'nav.group.platform',
};

export function AppSidebar({ currentModuleKey, collapsed, onToggleCollapse, displayName, onLogout }: AppSidebarProps) {
  const { t } = useTranslation('common');
  const groupedModules = getModulesByGroup();

  // Render groups in defined order
  const groupOrder: ModuleGroup[] = ['build', 'run', 'improve', 'platform'];

  return (
    <aside className={`admin-sidebar ${collapsed ? 'admin-sidebar--collapsed' : ''}`}>
      <div className="admin-sidebar__brand">
        <div className="admin-sidebar__brand-mark">AI</div>
        <div className="admin-sidebar__brand-text">
          <div className="admin-sidebar__brand-title">{t('nav.brandTitle')}</div>
          <div className="admin-sidebar__brand-subtitle">{t('nav.brandSubtitle')}</div>
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
              {!collapsed && (
                <div className="admin-sidebar__group-label">
                  {t(GROUP_LABEL_KEYS[group])}
                </div>
              )}
              {modules.map((module) => {
                const Icon = module.icon;
                const label = t(NAV_LABEL_KEYS[module.key]);
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
