import { ModuleLayoutShell } from '@/shared/ui/ModuleLayoutShell';
import { useTranslation } from 'react-i18next';

export function ObservabilityLayout() {
  const { t } = useTranslation(['common', 'observability']);
  const sections = [
    { key: 'traces', label: t('observability:sections.traces'), path: '/traces' },
  ];

  return (
    <ModuleLayoutShell
      eyebrow={t('observability:eyebrow')}
      title={t('observability:title')}
      sections={sections}
    />
  );
}
