import { CheckCircle, Circle, Loader2, XCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { getPipelineSteps, getPipelineStepsFromProgress, isDocumentStageKey } from '../../../lib/formatters';
import type { PipelineStep, ProcessingStage, StageProgressItem } from '../../../lib/formatters';

export function ProcessingPipeline({
  currentStage,
  stageProgress,
}: {
  currentStage: ProcessingStage;
  stageProgress?: StageProgressItem[];
}) {
  const { t } = useTranslation('knowledgeBase');
  // Prefer real backend progress data; fall back to legacy stage-based inference
  const steps: PipelineStep[] =
    (stageProgress && getPipelineStepsFromProgress(stageProgress)) ||
    getPipelineSteps(currentStage);

  return (
    <div className="space-y-1">
      {steps.map((step) => (
        <div key={step.stage} className="flex items-center gap-3 py-1.5">
          {step.status === 'done' && <CheckCircle size={16} className="shrink-0 text-success" />}
          {step.status === 'active' && <Loader2 size={16} className="shrink-0 animate-spin text-primary" />}
          {step.status === 'pending' && <Circle size={16} className="shrink-0 text-text-muted" />}
          {step.status === 'failed' && <XCircle size={16} className="shrink-0 text-error" />}
          <span
            className={
              step.status === 'active'
                ? 'font-medium text-text'
                : step.status === 'done'
                  ? 'text-text-secondary'
                  : step.status === 'failed'
                    ? 'text-error'
                    : 'text-text-muted'
            }
          >
            {isDocumentStageKey(step.label) ? t(step.label) : step.label}
          </span>
        </div>
      ))}
    </div>
  );
}
