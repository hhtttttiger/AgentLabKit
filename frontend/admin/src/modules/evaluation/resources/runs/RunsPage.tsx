import { useState } from 'react';
import { useRunList, useRunConfigList, useTriggerRun, useCreateRunConfig } from '../configs/hooks';
import { useDatasetList } from '../datasets/hooks';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { EmptyState } from '@/shared/ui/EmptyState';
import { SkeletonRows } from '@/shared/ui/Skeleton';
import { useToast } from '@/shared/ui/Toast';
import { RunConfigFormModal } from '../configs/RunConfigFormModal';
import type { CreateRunConfigDraft } from '../configs/RunConfigFormModal';
import { getErrorMessage } from '@/shared/api/errors';

const STATUS_COLORS: Record<string, string> = {
  pending: 'text-text-muted',
  running: 'text-warning',
  completed: 'text-success',
  failed: 'text-error',
};

export function RunsPage() {
  const { t } = useTranslation(['common', 'evaluation']);
  const { toast } = useToast();
  const navigate = useNavigate();
  const { data: runs, isLoading } = useRunList();
  const { data: configs } = useRunConfigList();
  const { data: datasetResult } = useDatasetList();
  const triggerMutation = useTriggerRun();
  const createConfigMutation = useCreateRunConfig();
  const [selectedConfig, setSelectedConfig] = useState('');
  const [createConfigOpen, setCreateConfigOpen] = useState(false);

  const datasets = datasetResult?.items ?? [];

  const handleCreateConfig = async (model: CreateRunConfigDraft) => {
    await createConfigMutation.mutateAsync({
      name: model.name,
      datasetId: model.datasetId,
      targetType: model.targetType,
      targetKey: model.targetKey,
      metricConfigs: model.metricConfigs.map((name) => ({ name })),
      judgeModelBindingKey: model.judgeModelBindingKey,
    });
    setCreateConfigOpen(false);
    toast(t('toast.created'));
  };

  return (
    <div className="flex flex-col gap-4 p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text">评估运行</h2>
        <div className="flex items-center gap-2">
          <select
            className="rounded-[2px] border border-border bg-background px-3 py-1.5 text-sm"
            value={selectedConfig}
            onChange={(e) => setSelectedConfig(e.target.value)}
          >
            <option value="">选择配置…</option>
            {configs?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <button
            onClick={() => selectedConfig && triggerMutation.mutate(selectedConfig, { onSuccess: () => toast(t('toast.operationSuccess')) })}
            disabled={!selectedConfig || triggerMutation.isPending}
            className="rounded-[2px] bg-primary px-3 py-1.5 text-xs text-background disabled:opacity-30"
          >
            运行评估
          </button>
          <button
            onClick={() => setCreateConfigOpen(true)}
            className="rounded-[2px] border border-border bg-surface px-3 py-1.5 text-xs text-text-secondary hover:bg-surface-raised"
          >
            新建配置
          </button>
        </div>
      </div>

      {isLoading ? (
        <SkeletonRows columns={6} rows={5} />
      ) : !runs?.length ? (
        <EmptyState title={t('evaluation:runs.emptyTitle')} description={t('evaluation:runs.emptyDescription')} />
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-text-muted">
              <th className="pb-2 font-medium">Run ID</th>
              <th className="pb-2 font-medium text-center">状态</th>
              <th className="pb-2 font-medium text-right">平均分</th>
              <th className="pb-2 font-medium text-right">用例数</th>
              <th className="pb-2 font-medium text-right">错误数</th>
              <th className="pb-2 font-medium">时间</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id} className="cursor-pointer border-b border-border-subtle last:border-0 hover:bg-surface-raised" onClick={() => navigate(`/evaluation/runs/${r.id}`)}>
                <td className="py-2 font-mono text-xs text-primary">#{r.id}</td>
                <td className={`py-2 text-center text-xs font-medium ${STATUS_COLORS[r.status] || ''}`}>{r.status}</td>
                <td className="py-2 text-right font-medium text-text">{((r.summary?.avgScore as number) ?? 0).toFixed(3)}</td>
                <td className="py-2 text-right text-text-secondary">{(r.summary?.total_cases as number) ?? '—'}</td>
                <td className="py-2 text-right text-text-secondary">{(r.summary?.error_count as number) ?? 0}</td>
                <td className="py-2 text-text-secondary">{r.createdAtUtc ? new Date(r.createdAtUtc).toLocaleString() : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <RunConfigFormModal
        open={createConfigOpen}
        datasets={datasets}
        loading={createConfigMutation.isPending}
        error={createConfigMutation.error ? getErrorMessage(createConfigMutation.error) : null}
        onClose={() => {
          setCreateConfigOpen(false);
          createConfigMutation.reset();
        }}
        onSubmit={handleCreateConfig}
      />
    </div>
  );
}
