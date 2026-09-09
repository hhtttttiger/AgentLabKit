import { ModuleLayoutShell } from '@/shared/ui/ModuleLayoutShell';
import { useTranslation } from 'react-i18next';

export function CostAnalysisLayout() {
  const { t } = useTranslation(['common', 'costAnalysis']);
  const sections = [
    { key: 'overview', label: t('costAnalysis:sections.overview'), path: '/cost' },
    { key: 'budgets', label: t('costAnalysis:sections.budgets'), path: '/cost/budgets' },
    { key: 'alerts', label: t('costAnalysis:sections.alerts'), path: '/cost/alerts' },
  ];

  return (
    <ModuleLayoutShell
      eyebrow={t('costAnalysis:eyebrow')}
      title={t('costAnalysis:title')}
      sections={sections}
    />
  );
}
