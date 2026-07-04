import { ModuleLayoutShell } from '@/shared/ui/ModuleLayoutShell';
import { useTranslation } from 'react-i18next';

export function GlossaryLayout() {
  const { t } = useTranslation('common');
  const sections = [
    { key: 'list', label: t('modules.glossary.sections.list'), path: '/glossary', end: true },
  ];

  return <ModuleLayoutShell eyebrow={t('modules.glossary.eyebrow')} title={t('modules.glossary.title')} sections={sections} />;
}
