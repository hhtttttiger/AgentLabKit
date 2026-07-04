import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Play, PlusCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/shared/ui/Button';
import { ModuleLayoutShell } from '@/shared/ui/ModuleLayoutShell';
import { isTextModel } from '@/shared/config/catalogOptions';
import { useModelDetail } from '../resources/model-cards/hooks';
import { ModelTestDialog } from '../resources/model-cards/ModelTestDialog';

export function ModelDetailLayout() {
  const { t } = useTranslation('common');
  const { modelKey } = useParams<{ modelKey: string }>();
  const navigate = useNavigate();
  const detailQuery = useModelDetail(modelKey);
  const [testOpen, setTestOpen] = useState(false);

  const model = detailQuery.data ?? null;
  const cardName = model?.displayName ?? t('modules.modelManagement.detail.fallbackTitle');

  const sections = [
    { key: 'overview', label: t('modules.modelManagement.detail.sections.overview'), path: `/model-management/models/${modelKey}`, end: true },
    { key: 'instances', label: t('modules.modelManagement.detail.sections.instances'), path: `/model-management/models/${modelKey}/instances` },
    { key: 'bindings', label: t('modules.modelManagement.detail.sections.bindings'), path: `/model-management/models/${modelKey}/bindings` },
  ];

  return (
    <>
      <ModuleLayoutShell
        eyebrow={t('modules.modelManagement.eyebrow')}
        title={cardName}
        sections={sections}
        leading={
          <button
            onClick={() => navigate('/model-management/models')}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-text-secondary transition hover:bg-state-hover hover:text-text"
            title={t('modules.modelManagement.detail.backToList')}
          >
            <ArrowLeft size={18} />
          </button>
        }
        actions={
          <div className="flex gap-2">
            {isTextModel(model?.type) && (
              <Button variant="secondary" onClick={() => setTestOpen(true)}>
                <Play size={16} />
                {t('modules.modelManagement.models.page.rowActions.test')}
              </Button>
            )}
            <Button onClick={() => navigate(`/model-management/models/${modelKey}/instances?action=create`)}>
              <PlusCircle size={16} />
              {t('actions.addInstance')}
            </Button>
            <Button variant="secondary" onClick={() => navigate(`/model-management/models/${modelKey}/bindings?action=create`)}>
              <PlusCircle size={16} />
              {t('actions.addBinding')}
            </Button>
          </div>
        }
      />
      <ModelTestDialog open={testOpen} model={model} onClose={() => setTestOpen(false)} />
    </>
  );
}
