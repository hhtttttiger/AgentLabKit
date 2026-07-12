import { ModuleLayoutShell } from '@/shared/ui/ModuleLayoutShell';
import { useTranslation } from 'react-i18next';

export function AgentManagementLayout() {
  const { t } = useTranslation(['common', 'agentManagement']);
  const sections = [
    { key: 'agents', label: t('agentManagement.sections.agents'), path: '/agent-management/agents' },
    { key: 'tools', label: t('agentManagement.sections.tools'), path: '/agent-management/tools' },
    { key: 'skills', label: t('agentManagement.sections.skills'), path: '/agent-management/skills' },
    { key: 'mcp-servers', label: t('agentManagement.sections.mcpServers'), path: '/agent-management/mcp-servers' },
  ];

  return (
    <ModuleLayoutShell eyebrow={t('agentManagement.eyebrow')} title={t('agentManagement.title')} sections={sections} />
  );
}
