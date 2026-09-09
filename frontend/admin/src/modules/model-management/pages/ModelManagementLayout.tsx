import { ModuleLayoutShell } from '@/shared/ui/ModuleLayoutShell';
import { useTranslation } from 'react-i18next';

export function ModelManagementLayout() {
  const { t } = useTranslation(['common', 'modelManagement']);
  const sections = [
    { key: 'cards', label: t('modelManagement:sections.cards'), path: '/models/models' },
    { key: 'instances', label: t('modelManagement:sections.instances'), path: '/models/model-instances' },
    { key: 'bindings', label: t('modelManagement:sections.bindings'), path: '/models/model-bindings' },
    { key: 'profiles', label: t('modelManagement:sections.profiles'), path: '/models/connection-profiles' },
    { key: 'features', label: t('modelManagement:sections.features'), path: '/models/features' },
  ];

  return (
    <ModuleLayoutShell eyebrow={t('modelManagement:eyebrow')} title={t('modelManagement:title')} sections={sections} />
  );
}
