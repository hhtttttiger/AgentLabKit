import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
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
  judgeModelKey: string;
}

const DEFAULT_METRICS = ['answer_relevance', 'faithfulness', 'context_relevance'] as const;

const emptyDraft: CreateRunConfigDraft = {
  name: 'Evaluation',
  datasetId: '',
  targetType: 'agent',
  targetKey: '',
  metricConfigs: [...DEFAULT_METRICS],
  judgeModelKey: '',
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
  const { t } = useTranslation(['common', 'evaluation']);
  const navigate = useNavigate();
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
      title={t('evaluation:runs.evaluateDataset')}
      description={t('evaluation:runs.formDescription')}
      onClose={onClose}
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose}>
            {t('common:actions.cancel')}
          </Button>
          <Button
            variant="primary"
            onClick={() => onSubmit(draft)}
            disabled={loading || !isValid}
          >
            {loading ? t('evaluation:runs.preparing') : t('evaluation:runs.runEvaluation')}
          </Button>
        </div>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <InlineMessage tone="error">{error}</InlineMessage>}

        {datasets.length === 0 && (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-[2px] border border-warning/30 bg-warning-subtle px-4 py-3 text-sm">
            <span className="text-text-secondary">{t('evaluation:runs.noDatasetsPrereq')}</span>
            <Button variant="secondary" onClick={() => navigate('/evaluation/datasets')}>
              {t('evaluation:overview.openDatasets')}
            </Button>
          </div>
        )}

        <SelectField
          label={t('evaluation:form.dataset')}
          value={draft.datasetId}
          onChange={(e) => setDraft((p) => ({ ...p, datasetId: e.target.value }))}
        >
          <option value="">{t('evaluation:runs.selectDataset')}</option>
          {datasets.map((ds) => (
            <option key={ds.id} value={ds.id}>
              {t('evaluation:runs.datasetOption', { name: ds.name, count: ds.caseCount })}
            </option>
          ))}
        </SelectField>

        {draft.targetType === 'agent' && (
          <SelectField
            label={t('evaluation:form.agent')}
            value={draft.targetKey}
            onChange={(e) => setDraft((p) => ({ ...p, targetKey: e.target.value }))}
          >
            <option value="">{t('evaluation:runs.selectAgent')}</option>
            {agents.map((agent) => <option key={agent.agentKey} value={agent.agentKey}>{agent.displayName} ({agent.agentKey})</option>)}
          </SelectField>
        )}

        <div>
          <label className="mb-1 block text-xs font-medium text-text-muted">
            {t('evaluation:runs.metrics')}
          </label>
          <div className="flex flex-wrap gap-2">
            {DEFAULT_METRICS.map((metric) => (
              <label
                key={metric}
                className="flex cursor-pointer items-center gap-1.5 rounded-[2px] border border-border bg-background px-3 py-1.5 text-xs"
              >
                <input
                  type="checkbox"
                  checked={draft.metricConfigs.includes(metric)}
                  onChange={() => toggleMetric(metric)}
                />
                {t(`evaluation:runs.metric.${metric}`)}
              </label>
            ))}
          </div>
        </div>

        <details className="border-t border-border pt-3">
          <summary className="cursor-pointer text-sm font-medium text-text">{t('evaluation:form.advanced')}</summary>
          <div className="mt-3 flex flex-col gap-4">
            <TextField
              label={t('evaluation:form.configurationName')}
              value={draft.name}
              onChange={(e) => setDraft((p) => ({ ...p, name: e.target.value }))}
              placeholder="Evaluation"
            />
            <SelectField
              label={t('evaluation:form.targetMode')}
              value={draft.targetType}
              onChange={(e) => setDraft((p) => ({ ...p, targetType: e.target.value as 'agent' | 'rag_pipeline' }))}
            >
              <option value="agent">Agent</option>
              <option value="rag_pipeline">RAG Pipeline</option>
            </SelectField>
            {draft.targetType === 'rag_pipeline' && (
              <TextField
                label={t('evaluation:form.ragPipeline')}
                value={draft.targetKey}
                onChange={(e) => setDraft((p) => ({ ...p, targetKey: e.target.value }))}
                placeholder={t('evaluation:runs.ragPipelinePlaceholder')}
              />
            )}
            <TextField
              label={t('evaluation:form.judgeBinding')}
              value={draft.judgeModelKey}
              onChange={(e) => setDraft((p) => ({ ...p, judgeModelKey: e.target.value }))}
              placeholder={t('evaluation:runs.judgePlaceholder')}
              hint={t('evaluation:runs.judgeHint')}
            />
          </div>
        </details>
      </div>
    </FormModal>
  );
}
