import { ModuleLayoutShell } from '@/shared/ui/ModuleLayoutShell';
import { useTranslation } from 'react-i18next';

export function ModelManagementLayout() {
  const { t } = useTranslation('common');
  const sections = [
    { key: 'cards', label: t('modules.modelManagement.sections.cards'), path: '/model-management/models' },
    { key: 'instances', label: t('modules.modelManagement.sections.instances'), path: '/model-management/model-instances' },
    { key: 'bindings', label: t('modules.modelManagement.sections.bindings'), path: '/model-management/model-bindings' },
    { key: 'profiles', label: t('modules.modelManagement.sections.profiles'), path: '/model-management/connection-profiles' },
    { key: 'features', label: t('modules.modelManagement.sections.features'), path: '/model-management/features' },
  ];

  return (
    <ModuleLayoutShell eyebrow={t('modules.modelManagement.eyebrow')} title={t('modules.modelManagement.title')} sections={sections} />
  );
}
