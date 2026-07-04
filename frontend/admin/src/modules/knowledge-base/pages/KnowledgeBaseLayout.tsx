import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Pencil } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/shared/ui/Button';
import { useToast } from '@/shared/ui/Toast';
import { useKbDetail, useKbMutations } from '../resources/knowledge-base/hooks';
import { KbCreateDrawer } from '../resources/knowledge-base/components/KbCreateDrawer';
import { ModuleLayoutShell } from '@/shared/ui/ModuleLayoutShell';

export function KnowledgeBaseLayout() {
  const { t } = useTranslation('common');
  const { kbId } = useParams<{ kbId: string }>();
  const navigate = useNavigate();
  const detailQuery = useKbDetail(kbId);
  const mutations = useKbMutations();
  const { toast } = useToast();
  const [editOpen, setEditOpen] = useState(false);

  const tabs = [
    { key: 'overview', label: t('modules.knowledgeBase.detail.sections.overview'), path: `/knowledge-base/${kbId}` },
    { key: 'documents', label: t('modules.knowledgeBase.detail.sections.documents'), path: `/knowledge-base/${kbId}/documents` },
    { key: 'glossary', label: t('modules.knowledgeBase.detail.sections.glossary'), path: `/knowledge-base/${kbId}/glossary` },
    { key: 'search', label: t('modules.knowledgeBase.detail.sections.search'), path: `/knowledge-base/${kbId}/search` },
  ];

  const kbName = detailQuery.data?.name ?? t('modules.knowledgeBase.detail.fallbackTitle');
  const kb = detailQuery.data;

  return (
    <>
      <ModuleLayoutShell
        eyebrow={t('modules.knowledgeBase.detail.eyebrow')}
        title={kbName}
        sections={tabs}
        leading={
          <button
            onClick={() => navigate('/knowledge-base')}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-text-secondary transition hover:bg-state-hover hover:text-text"
            title={t('modules.knowledgeBase.detail.backToList')}
          >
            <ArrowLeft size={18} />
          </button>
        }
        actions={
          kb ? (
            <Button variant="secondary" onClick={() => setEditOpen(true)}>
              <Pencil size={16} />
              {t('actions.edit')}
            </Button>
          ) : null
        }
      />

      {kb ? (
        <KbCreateDrawer
          open={editOpen}
          mode="edit"
          initialValue={kb}
          loading={mutations.update.isPending}
          onSubmit={(data) =>
            mutations.update.mutate(
              { kbId: kb.id, data },
              {
                onSuccess: () => {
                  toast(t('modules.knowledgeBase.detail.updateSuccess'));
                  setEditOpen(false);
                },
                onError: () => toast(t('modules.knowledgeBase.detail.updateFailed'), 'error'),
              },
            )
          }
          onClose={() => setEditOpen(false)}
        />
      ) : null}
    </>
  );
}
