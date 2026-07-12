import { ModuleLayoutShell } from '@/shared/ui/ModuleLayoutShell';
import { useTranslation } from 'react-i18next';

export function ModelManagementLayout() {
  const { t } = useTranslation(['common', 'modelManagement']);
  const sections = [
    { key: 'cards', label: t('modelManagement:sections.cards'), path: '/model-management/models' },
    { key: 'instances', label: t('modelManagement:sections.instances'), path: '/model-management/model-instances' },
    { key: 'bindings', label: t('modelManagement:sections.bindings'), path: '/model-management/model-bindings' },
    { key: 'profiles', label: t('modelManagement:sections.profiles'), path: '/model-management/connection-profiles' },
    { key: 'features', label: t('modelManagement:sections.features'), path: '/model-management/features' },
  ];

  return (
    <ModuleLayoutShell eyebrow={t('modelManagement:eyebrow')} title={t('modelManagement:title')} sections={sections} />
  );
}
