import { useEffect, useState } from 'react';
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
  name: '',
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
}: RunConfigFormModalProps) {
  const [draft, setDraft] = useState<CreateRunConfigDraft>(emptyDraft);

  useEffect(() => {
    if (open) setDraft(emptyDraft);
  }, [open]);

  const toggleMetric = (name: string) => {
    setDraft((prev) => ({
      ...prev,
      metricConfigs: prev.metricConfigs.includes(name)
        ? prev.metricConfigs.filter((m) => m !== name)
        : [...prev.metricConfigs, name],
    }));
  };

  const isValid = draft.name.trim() && draft.datasetId && draft.targetKey.trim();

  return (
    <FormModal
      open={open}
      title="新建运行配置"
      description="创建评估运行配置以对数据集执行自动化评估"
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
            {loading ? '提交中...' : '创建'}
          </Button>
        </div>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <InlineMessage tone="error">{error}</InlineMessage>}

        <TextField
          label="配置名称"
          value={draft.name}
          onChange={(e) => setDraft((p) => ({ ...p, name: e.target.value }))}
          placeholder="例如：QA 测试 v1"
        />

        <SelectField
          label="数据集"
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

        <SelectField
          label="目标类型"
          value={draft.targetType}
          onChange={(e) =>
            setDraft((p) => ({
              ...p,
              targetType: e.target.value as 'agent' | 'rag_pipeline',
            }))
          }
        >
          <option value="agent">Agent</option>
          <option value="rag_pipeline">RAG Pipeline</option>
        </SelectField>

        <TextField
          label={draft.targetType === 'agent' ? 'Agent Key' : '知识库 ID'}
          value={draft.targetKey}
          onChange={(e) => setDraft((p) => ({ ...p, targetKey: e.target.value }))}
          placeholder={draft.targetType === 'agent' ? '例如：qa-bot' : '例如：kb-123'}
          hint={draft.targetType === 'agent' ? '对应 Agent 定义的 agent_key' : '对应知识库的 ID'}
        />

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

        <TextField
          label="Judge 模型 (可选)"
          value={draft.judgeModelBindingKey}
          onChange={(e) => setDraft((p) => ({ ...p, judgeModelBindingKey: e.target.value }))}
          placeholder="留空则使用默认模型"
          hint="LLM-as-Judge 使用的模型 binding key"
        />
      </div>
    </FormModal>
  );
}
