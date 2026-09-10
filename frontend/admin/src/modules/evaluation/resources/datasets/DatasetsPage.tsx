import { useState } from 'react';
import { useDatasetList, useCreateDataset, useDeleteDataset } from './hooks';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Plus } from 'lucide-react';
import { Button } from '@/shared/ui/Button';
import { EmptyState } from '@/shared/ui/EmptyState';
import { SkeletonRows } from '@/shared/ui/Skeleton';
import { useToast } from '@/shared/ui/Toast';
import { formatAdminDateTime } from '@/shared/i18n/formatters';

export function DatasetsPage() {
  const { t } = useTranslation(['common', 'evaluation']);
  const { toast } = useToast();
  const navigate = useNavigate();
  const { data: result, isLoading } = useDatasetList();
  const createMutation = useCreateDataset();
  const deleteMutation = useDeleteDataset();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');

  const datasets = result?.items ?? [];

  const handleCreate = async () => {
    if (!name.trim()) return;
    await createMutation.mutateAsync({ name: name.trim(), description: desc.trim() || undefined });
    setName(''); setDesc(''); setShowForm(false);
    toast(t('toast.created'));
  };

  return (
    <div className="flex flex-col gap-4 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-text">{t('evaluation:datasets.title')}</h2>
          <p className="mt-1 text-sm text-text-secondary">{t('evaluation:datasets.description')}</p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>
          <Plus size={14} />
          {showForm ? t('common:actions.cancel') : t('evaluation:datasets.createDataset')}
        </Button>
      </div>

      {showForm && (
        <div className="flex gap-3 rounded-[2px] border border-border bg-surface p-4">
          <input
            className="flex-1 rounded-[2px] border border-border bg-background px-3 py-2 text-sm"
            placeholder={t('evaluation:datasets.namePlaceholder')}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <input
            className="flex-1 rounded-[2px] border border-border bg-background px-3 py-2 text-sm"
            placeholder={t('evaluation:datasets.descriptionPlaceholder')}
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
          />
          <button
            onClick={handleCreate}
            disabled={createMutation.isPending || !name.trim()}
            className="rounded-[2px] bg-primary px-4 py-2 text-xs text-primary-foreground disabled:opacity-30"
          >
            {t('common:actions.create')}
          </button>
        </div>
      )}

      {isLoading ? (
        <SkeletonRows columns={5} rows={5} />
      ) : !datasets.length ? (
        <EmptyState
          title={t('evaluation:datasets.emptyTitle')}
          description={t('evaluation:datasets.emptyDescription')}
          action={
            <Button onClick={() => setShowForm(true)}>
              <Plus size={14} />
              {t('evaluation:datasets.createDataset')}
            </Button>
          }
        />
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-text-muted">
              <th className="pb-2 font-medium">{t('evaluation:datasets.columns.name')}</th>
              <th className="pb-2 font-medium">{t('evaluation:datasets.columns.description')}</th>
              <th className="pb-2 font-medium text-center">{t('evaluation:datasets.columns.itemCount')}</th>
              <th className="pb-2 font-medium">{t('evaluation:datasets.columns.createdAt')}</th>
              <th className="pb-2 font-medium text-right">{t('evaluation:datasets.columns.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {datasets.map((ds) => (
              <tr key={ds.id} className="border-b border-border-subtle last:border-0">
                <td className="py-2 font-medium text-text">{ds.name}</td>
                <td className="py-2 text-text-secondary">{ds.description || '—'}</td>
                <td className="py-2 text-center text-text-secondary">{ds.caseCount}</td>
                <td className="py-2 text-text-secondary">{formatAdminDateTime(ds.createdAtUtc)}</td>
                <td className="py-2 text-right">
                  <button onClick={() => navigate(`/evaluation/dataset/${ds.id}`)} className="mr-3 text-xs text-primary hover:underline">{t('evaluation:datasets.actions.view')}</button>
                  <button onClick={() => deleteMutation.mutate(ds.id, { onSuccess: () => toast(t('toast.deleted')) })} className="text-xs text-error hover:underline">{t('evaluation:datasets.actions.delete')}</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
