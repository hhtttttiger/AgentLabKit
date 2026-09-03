/**
 * Capabilities Layout — Tab navigation for Tools, Skills, MCP
 */

import { NavLink, Outlet } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { cn } from '@/shared/lib/cn';

export function CapabilitiesLayout() {
  const { t } = useTranslation(['common', 'capabilities']);

  const tabs = [
    { path: '/capabilities/tools', label: t('capabilities:tabs.tools') },
    { path: '/capabilities/skills', label: t('capabilities:tabs.skills') },
    { path: '/capabilities/mcp', label: t('capabilities:tabs.mcp') },
  ];

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-border bg-surface px-6 py-4">
        <h1 className="text-lg font-semibold text-text">{t('capabilities:title')}</h1>
        <p className="mt-1 text-sm text-text-secondary">{t('capabilities:subtitle')}</p>
      </div>

      {/* Tabs */}
      <div className="border-b border-border bg-surface px-6">
        <nav className="flex gap-1">
          {tabs.map((tab) => (
            <NavLink
              key={tab.path}
              to={tab.path}
              className={({ isActive }) =>
                cn(
                  'border-b-2 px-4 py-3 text-sm font-medium transition',
                  isActive
                    ? 'border-primary text-primary'
                    : 'border-transparent text-text-muted hover:text-text',
                )
              }
            >
              {tab.label}
            </NavLink>
          ))}
        </nav>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <Outlet />
      </div>
    </div>
  );
}
