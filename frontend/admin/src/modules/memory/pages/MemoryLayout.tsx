import { useMemo } from 'react';
import { ModuleLayoutShell } from '@/shared/ui/ModuleLayoutShell';
import { useTranslation } from 'react-i18next';

export function MemoryLayout() {
  const { t } = useTranslation('common');
  const sections = useMemo(
    () => [
      { key: 'memories', label: t('modules.memory.sections.memories'), path: '/memory' },
    ],
    [t],
  );

  return (
    <ModuleLayoutShell
      eyebrow={t('modules.memory.eyebrow')}
      title={t('modules.memory.title')}
      sections={sections}
    />
  );
}
