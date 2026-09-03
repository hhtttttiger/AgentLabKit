import { ModuleLayoutShell } from '@/shared/ui/ModuleLayoutShell';
import { useTranslation } from 'react-i18next';

export function AgentManagementLayout() {
  const { t } = useTranslation(['common', 'agentManagement']);
  const sections = [
    { key: 'agents', label: t('agentManagement.sections.agents'), path: '/agents' },
  ];

  return (
    <ModuleLayoutShell eyebrow={t('agentManagement.eyebrow')} title={t('agentManagement.title')} sections={sections} />
  );
}
