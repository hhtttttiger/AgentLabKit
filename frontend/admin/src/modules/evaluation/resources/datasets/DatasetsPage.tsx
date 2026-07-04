import { useState } from 'react';
import { useDatasetList, useCreateDataset, useDeleteDataset } from './hooks';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { EmptyState } from '@/shared/ui/EmptyState';
import { SkeletonRows } from '@/shared/ui/Skeleton';
import { useToast } from '@/shared/ui/Toast';

export function DatasetsPage() {
  const { t } = useTranslation('common');
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
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text">数据集</h2>
        <button onClick={() => setShowForm(!showForm)} className="rounded-[2px] bg-primary px-3 py-1.5 text-xs text-background">
          {showForm ? '取消' : '新建数据集'}
        </button>
      </div>

      {showForm && (
        <div className="flex gap-3 rounded-[2px] border border-border bg-surface p-4">
          <input className="flex-1 rounded-[2px] border border-border bg-background px-3 py-2 text-sm" placeholder="数据集名称" value={name} onChange={(e) => setName(e.target.value)} />
          <input className="flex-1 rounded-[2px] border border-border bg-background px-3 py-2 text-sm" placeholder="描述（可选）" value={desc} onChange={(e) => setDesc(e.target.value)} />
          <button onClick={handleCreate} disabled={createMutation.isPending} className="rounded-[2px] bg-primary px-4 py-2 text-xs text-background">
            创建
          </button>
        </div>
      )}

      {isLoading ? (
        <SkeletonRows columns={5} rows={5} />
      ) : !datasets.length ? (
        <EmptyState title={t('modules.evaluation.datasets.emptyTitle')} description={t('modules.evaluation.datasets.emptyDescription')} />
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-text-muted">
              <th className="pb-2 font-medium">名称</th>
              <th className="pb-2 font-medium">描述</th>
              <th className="pb-2 font-medium text-center">用例数</th>
              <th className="pb-2 font-medium">创建时间</th>
              <th className="pb-2 font-medium text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            {datasets.map((ds) => (
              <tr key={ds.id} className="border-b border-border-subtle last:border-0">
                <td className="py-2 font-medium text-text">{ds.name}</td>
                <td className="py-2 text-text-secondary">{ds.description || '—'}</td>
                <td className="py-2 text-center text-text-secondary">{ds.caseCount}</td>
                <td className="py-2 text-text-secondary">{new Date(ds.createdAtUtc).toLocaleString()}</td>
                <td className="py-2 text-right">
                  <button onClick={() => navigate(`/evaluation/dataset/${ds.id}`)} className="mr-3 text-xs text-primary hover:underline">查看</button>
                  <button onClick={() => deleteMutation.mutate(ds.id, { onSuccess: () => toast(t('toast.deleted')) })} className="text-xs text-error hover:underline">删除</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
