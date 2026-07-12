import { NavLink } from 'react-router-dom';
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { UserMenu } from '@/shared/ui/UserMenu';
import { appModules } from '../modules';
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
  'ai-chat': 'nav.aiChat',
  'agent-management': 'nav.agentManagement',
  'model-management': 'nav.modelManagement',
  glossary: 'nav.glossary',
  'knowledge-base': 'nav.knowledgeBase',
  'model-monitoring': 'nav.modelMonitoring',
  'cost-analysis': 'nav.costAnalysis',
  observability: 'nav.observability',
  memory: 'nav.memory',
  evaluation: 'nav.evaluation',
  'user-management': 'nav.userManagement',
} as const;

export function AppSidebar({ currentModuleKey, collapsed, onToggleCollapse, displayName, onLogout }: AppSidebarProps) {
  const { t } = useTranslation('common');

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
        {appModules.map((module) => {
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
