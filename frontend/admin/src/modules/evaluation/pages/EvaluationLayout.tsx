import { ModuleLayoutShell } from '@/shared/ui/ModuleLayoutShell';
import { useTranslation } from 'react-i18next';

export function EvaluationLayout() {
  const { t } = useTranslation(['common', 'evaluation']);
  const sections = [
    { key: 'overview', label: t('evaluation:sections.overview'), path: '/evaluation/overview' },
    { key: 'datasets', label: t('evaluation:sections.datasets'), path: '/evaluation/datasets' },
    { key: 'runs', label: t('evaluation:sections.runs'), path: '/evaluation/runs' },
  ];

  return (
    <ModuleLayoutShell
      eyebrow={t('evaluation:eyebrow')}
      title={t('evaluation:title')}
      sections={sections}
    />
  );
}
