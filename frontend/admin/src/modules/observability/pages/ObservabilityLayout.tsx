import { ModuleLayoutShell } from '@/shared/ui/ModuleLayoutShell';
import { useTranslation } from 'react-i18next';

export function ObservabilityLayout() {
  const { t } = useTranslation('common');
  const sections = [
    { key: 'traces', label: t('modules.observability.sections.traces'), path: '/observability' },
  ];

  return (
    <ModuleLayoutShell
      eyebrow={t('modules.observability.eyebrow')}
      title={t('modules.observability.title')}
      sections={sections}
    />
  );
}
