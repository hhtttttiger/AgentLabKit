import { useMemo } from 'react';
import { ModuleLayoutShell } from '@/shared/ui/ModuleLayoutShell';
import { useTranslation } from 'react-i18next';

export function MemoryLayout() {
  const { t } = useTranslation(['common', 'memory']);
  const sections = useMemo(
    () => [
      { key: 'memories', label: t('memory:sections.memories'), path: '/memory' },
    ],
    [t],
  );

  return (
    <ModuleLayoutShell
      eyebrow={t('memory:eyebrow')}
      title={t('memory:title')}
      sections={sections}
    />
  );
}
