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
import { formatAdminDateTime } from '@/shared/i18n/formatters';
import { useAgentList } from '@/modules/agent-management/resources/agents/hooks';

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
  const { data: agents } = useAgentList({ status: 'published', page: 1, pageSize: 100 });
  const triggerMutation = useTriggerRun();
  const createConfigMutation = useCreateRunConfig();
  const [selectedConfig, setSelectedConfig] = useState('');
  const [selectedRuns, setSelectedRuns] = useState<string[]>([]);
  const [createConfigOpen, setCreateConfigOpen] = useState(false);
  const [evaluateOpen, setEvaluateOpen] = useState(false);

  const datasets = datasetResult?.items ?? [];
  const selectedDatasetId = selectedRuns.length ? configs?.find((config) => String(config.id) === String(runs?.find((run) => String(run.id) === selectedRuns[0])?.configId))?.datasetId : undefined;

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

  const handleEvaluate = async (model: CreateRunConfigDraft) => {
    const config = await createConfigMutation.mutateAsync({ name: model.name, datasetId: model.datasetId, targetType: model.targetType, targetKey: model.targetKey, metricConfigs: model.metricConfigs.map((name) => ({ name })), judgeModelBindingKey: model.judgeModelBindingKey });
    const run = await triggerMutation.mutateAsync(config.id);
    setEvaluateOpen(false);
    navigate(`/evaluation/runs/${run.id}`);
  };

  return (
    <div className="flex flex-col gap-4 p-6">
      <div className="flex items-center justify-between gap-4">
        <div><h1 className="text-lg font-semibold text-text">Evaluation Runs</h1>{selectedRuns.length === 2 && <button type="button" onClick={() => navigate(`/evaluation/runs/compare?left=${selectedRuns[0]}&right=${selectedRuns[1]}`)} className="mt-1 text-xs text-primary hover:underline">Compare selected runs</button>}</div>
        <div className="flex items-center gap-2">
          <button type="button" onClick={() => setEvaluateOpen(true)} className="rounded-[2px] bg-primary px-3 py-1.5 text-sm text-background">New Evaluation</button>
          <select
            className="rounded-[2px] border border-border bg-background px-3 py-1.5 text-sm"
            value={selectedConfig}
            onChange={(e) => setSelectedConfig(e.target.value)}
          >
            <option value="">选择配置…</option>
            {configs?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <button
            onClick={() => selectedConfig && triggerMutation.mutate(selectedConfig, { onSuccess: (run) => navigate(`/evaluation/runs/${run.id}`) })}
            disabled={!selectedConfig || triggerMutation.isPending}
            className="rounded-[2px] bg-primary px-3 py-1.5 text-xs text-background disabled:opacity-30"
          >
            Run saved configuration
          </button>
          <button
            onClick={() => setCreateConfigOpen(true)}
            className="rounded-[2px] border border-border bg-surface px-3 py-1.5 text-xs text-text-secondary hover:bg-surface-raised"
          >
            Saved configurations
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
              <th className="w-10 pb-2 font-medium" aria-label="Select" />
              <th className="pb-2 font-medium">Run</th>
              <th className="pb-2 font-medium">Agent</th>
              <th className="pb-2 font-medium">Dataset</th>
              <th className="pb-2 font-medium text-center">Status</th>
              <th className="pb-2 font-medium text-right">平均分</th>
              <th className="pb-2 font-medium text-right">用例数</th>
              <th className="pb-2 font-medium text-right">错误数</th>
              <th className="pb-2 font-medium">时间</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id} className="cursor-pointer border-b border-border-subtle last:border-0 hover:bg-surface-raised" onClick={() => navigate(`/evaluation/runs/${r.id}`)}>
                <td className="py-2 pl-2"><input type="checkbox" disabled={selectedDatasetId !== undefined && String(configs?.find((config) => String(config.id) === String(r.configId))?.datasetId) !== String(selectedDatasetId)} checked={selectedRuns.includes(String(r.id))} onChange={() => setSelectedRuns((current) => current.includes(String(r.id)) ? current.filter((id) => id !== String(r.id)) : current.length < 2 ? [...current, String(r.id)] : current)} onClick={(event) => event.stopPropagation()} aria-label={`Select evaluation run ${r.id}`} /></td>
                <td className="py-2 font-mono text-xs text-primary">#{r.id}</td>
                <td className="py-2 text-text">{configs?.find((config) => String(config.id) === String(r.configId))?.targetKey ?? '—'}</td>
                <td className="py-2 text-text-secondary">{datasets.find((dataset) => String(dataset.id) === String(configs?.find((config) => String(config.id) === String(r.configId))?.datasetId))?.name ?? '—'}</td>
                <td className={`py-2 text-center text-xs font-medium ${STATUS_COLORS[r.status] || ''}`}>{r.status}</td>
                <td className="py-2 text-right font-medium text-text">{typeof r.summary?.avgScore === 'number' ? (r.summary.avgScore as number).toFixed(3) : '—'}</td>
                <td className="py-2 text-right text-text-secondary">{(r.summary?.total_cases as number) ?? '—'}</td>
                <td className="py-2 text-right text-text-secondary">{typeof r.summary?.error_count === 'number' ? r.summary.error_count as number : '—'}</td>
                <td className="py-2 text-text-secondary">{formatAdminDateTime(r.createdAtUtc)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <RunConfigFormModal
        open={evaluateOpen}
        datasets={datasets}
        agents={agents?.items ?? []}
        loading={createConfigMutation.isPending || triggerMutation.isPending}
        error={createConfigMutation.error || triggerMutation.error ? '无法启动评估，请重试。' : null}
        onClose={() => { setEvaluateOpen(false); createConfigMutation.reset(); triggerMutation.reset(); }}
        onSubmit={handleEvaluate}
      />

      <RunConfigFormModal
        open={createConfigOpen}
        datasets={datasets}
        agents={agents?.items ?? []}
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
