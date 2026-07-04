import { ModuleLayoutShell } from '@/shared/ui/ModuleLayoutShell';
import { useTranslation } from 'react-i18next';

export function CostAnalysisLayout() {
  const { t } = useTranslation('common');
  const sections = [
    { key: 'overview', label: t('modules.costAnalysis.sections.overview'), path: '/cost-analysis' },
    { key: 'budgets', label: t('modules.costAnalysis.sections.budgets'), path: '/cost-analysis/budgets' },
    { key: 'alerts', label: t('modules.costAnalysis.sections.alerts'), path: '/cost-analysis/alerts' },
  ];

  return (
    <ModuleLayoutShell
      eyebrow={t('modules.costAnalysis.eyebrow')}
      title={t('modules.costAnalysis.title')}
      sections={sections}
    />
  );
}
