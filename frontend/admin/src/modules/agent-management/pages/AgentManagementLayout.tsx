import { ModuleLayoutShell } from '@/shared/ui/ModuleLayoutShell';
import { useTranslation } from 'react-i18next';

export function AgentManagementLayout() {
  const { t } = useTranslation('common');
  const sections = [
    { key: 'agents', label: t('modules.agentManagement.sections.agents'), path: '/agent-management/agents' },
    { key: 'tools', label: t('modules.agentManagement.sections.tools'), path: '/agent-management/tools' },
    { key: 'skills', label: t('modules.agentManagement.sections.skills'), path: '/agent-management/skills' },
    { key: 'mcp-servers', label: t('modules.agentManagement.sections.mcpServers'), path: '/agent-management/mcp-servers' },
  ];

  return (
    <ModuleLayoutShell eyebrow={t('modules.agentManagement.eyebrow')} title={t('modules.agentManagement.title')} sections={sections} />
  );
}
