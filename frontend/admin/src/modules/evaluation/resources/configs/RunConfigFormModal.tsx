import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FormModal } from '@/shared/ui/FormModal';
import { Button } from '@/shared/ui/Button';
import { SelectField, TextField } from '@/shared/ui/FormFields';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import type { DatasetData } from '../../lib/contracts';

interface RunConfigFormModalProps {
  open: boolean;
  datasets: DatasetData[];
  loading: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (model: CreateRunConfigDraft) => Promise<void>;
  initialDatasetId?: string;
  agents?: Array<{ agentKey: string; displayName: string }>;
}

export interface CreateRunConfigDraft {
  name: string;
  datasetId: string;
  targetType: 'agent' | 'rag_pipeline';
  targetKey: string;
  metricConfigs: string[];
  judgeModelBindingKey: string;
}

const DEFAULT_METRICS = [
  { name: 'answer_relevance', label: '答案相关性' },
  { name: 'faithfulness', label: '忠实度' },
  { name: 'context_relevance', label: '上下文相关性' },
];

const emptyDraft: CreateRunConfigDraft = {
  name: 'Evaluation',
  datasetId: '',
  targetType: 'agent',
  targetKey: '',
  metricConfigs: DEFAULT_METRICS.map((m) => m.name),
  judgeModelBindingKey: '',
};

export function RunConfigFormModal({
  open,
  datasets,
  loading,
  error,
  onClose,
  onSubmit,
  initialDatasetId,
  agents = [],
}: RunConfigFormModalProps) {
  const { t } = useTranslation('evaluation');
  const [draft, setDraft] = useState<CreateRunConfigDraft>(emptyDraft);

  useEffect(() => {
    if (open) setDraft({ ...emptyDraft, datasetId: initialDatasetId ?? '' });
  }, [open, initialDatasetId]);

  const toggleMetric = (name: string) => {
    setDraft((prev) => ({
      ...prev,
      metricConfigs: prev.metricConfigs.includes(name)
        ? prev.metricConfigs.filter((m) => m !== name)
        : [...prev.metricConfigs, name],
    }));
  };

  const isValid = draft.datasetId && draft.targetKey.trim() && draft.metricConfigs.length > 0;

  return (
    <FormModal
      open={open}
      title="Evaluate Dataset"
      description="选择数据集、Agent 和指标，然后运行评估。配置会保存下来供后续 Run Again 使用。"
      onClose={onClose}
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose}>
            取消
          </Button>
          <Button
            variant="primary"
            onClick={() => onSubmit(draft)}
            disabled={loading || !isValid}
          >
            {loading ? '运行准备中...' : 'Run Evaluation'}
          </Button>
        </div>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <InlineMessage tone="error">{error}</InlineMessage>}

        <SelectField
          label={t('form.dataset')}
          value={draft.datasetId}
          onChange={(e) => setDraft((p) => ({ ...p, datasetId: e.target.value }))}
        >
          <option value="">选择数据集...</option>
          {datasets.map((ds) => (
            <option key={ds.id} value={ds.id}>
              {ds.name} ({ds.caseCount} 条用例)
            </option>
          ))}
        </SelectField>

        {draft.targetType === 'agent' && (
          <SelectField
            label={t('form.agent')}
            value={draft.targetKey}
            onChange={(e) => setDraft((p) => ({ ...p, targetKey: e.target.value }))}
          >
            <option value="">选择 Agent...</option>
            {agents.map((agent) => <option key={agent.agentKey} value={agent.agentKey}>{agent.displayName} ({agent.agentKey})</option>)}
          </SelectField>
        )}

        <div>
          <label className="mb-1 block text-xs font-medium text-text-muted">
            评估指标
          </label>
          <div className="flex flex-wrap gap-2">
            {DEFAULT_METRICS.map((metric) => (
              <label
                key={metric.name}
                className="flex cursor-pointer items-center gap-1.5 rounded-[2px] border border-border bg-background px-3 py-1.5 text-xs"
              >
                <input
                  type="checkbox"
                  checked={draft.metricConfigs.includes(metric.name)}
                  onChange={() => toggleMetric(metric.name)}
                />
                {metric.label}
              </label>
            ))}
          </div>
        </div>

        <details className="border-t border-border pt-3">
          <summary className="cursor-pointer text-sm font-medium text-text">{t('form.advanced')}</summary>
          <div className="mt-3 flex flex-col gap-4">
            <TextField
              label={t('form.configurationName')}
              value={draft.name}
              onChange={(e) => setDraft((p) => ({ ...p, name: e.target.value }))}
              placeholder="Evaluation"
            />
            <SelectField
              label={t('form.targetMode')}
              value={draft.targetType}
              onChange={(e) => setDraft((p) => ({ ...p, targetType: e.target.value as 'agent' | 'rag_pipeline' }))}
            >
              <option value="agent">Agent</option>
              <option value="rag_pipeline">RAG Pipeline</option>
            </SelectField>
            {draft.targetType === 'rag_pipeline' && (
              <TextField
                label={t('form.ragPipeline')}
                value={draft.targetKey}
                onChange={(e) => setDraft((p) => ({ ...p, targetKey: e.target.value }))}
                placeholder="例如：kb-123"
              />
            )}
            <TextField
              label={t('form.judgeBinding')}
              value={draft.judgeModelBindingKey}
              onChange={(e) => setDraft((p) => ({ ...p, judgeModelBindingKey: e.target.value }))}
              placeholder="留空则使用默认模型"
              hint="LLM-as-Judge 使用的模型 binding key"
            />
          </div>
        </details>
      </div>
    </FormModal>
  );
}
