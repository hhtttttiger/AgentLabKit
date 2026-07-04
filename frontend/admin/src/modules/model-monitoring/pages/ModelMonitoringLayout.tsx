import { ModuleLayoutShell } from '@/shared/ui/ModuleLayoutShell';
import { useTranslation } from 'react-i18next';

export function ModelMonitoringLayout() {
  const { t } = useTranslation('common');
  const sections = [
    { key: 'overview', label: t('modules.modelMonitoring.sections.overview'), path: '/model-monitoring' },
    { key: 'errors', label: t('modules.modelMonitoring.sections.errors'), path: '/model-monitoring/errors' },
  ];

  return (
    <ModuleLayoutShell eyebrow={t('modules.modelMonitoring.eyebrow')} title={t('modules.modelMonitoring.title')} sections={sections} />
  );
}
