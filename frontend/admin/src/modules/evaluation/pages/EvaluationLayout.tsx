import { ModuleLayoutShell } from '@/shared/ui/ModuleLayoutShell';
import { useTranslation } from 'react-i18next';

export function EvaluationLayout() {
  const { t } = useTranslation('common');
  const sections = [
    { key: 'datasets', label: t('modules.evaluation.sections.datasets'), path: '/evaluation' },
    { key: 'runs', label: t('modules.evaluation.sections.runs'), path: '/evaluation/runs' },
  ];

  return (
    <ModuleLayoutShell
      eyebrow={t('modules.evaluation.eyebrow')}
      title={t('modules.evaluation.title')}
      sections={sections}
    />
  );
}
