import { ModuleLayoutShell } from '@/shared/ui/ModuleLayoutShell';
import { useTranslation } from 'react-i18next';

export function GlossaryLayout() {
  const { t } = useTranslation(['common', 'glossary']);
  const sections = [
    { key: 'list', label: t('glossary:sections.list'), path: '/glossary', end: true },
  ];

  return <ModuleLayoutShell eyebrow={t('glossary:eyebrow')} title={t('glossary:title')} sections={sections} />;
}
