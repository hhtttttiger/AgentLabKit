// ── File size ──

export function formatFileSize(bytes: number | undefined | null): string {
  if (bytes == null || bytes === 0) return '-';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

// ── Processing pipeline ──

export type ProcessingStage =
  | 'Pending'
  | 'Loading'
  | 'Splitting'
  | 'Indexing'
  | 'GraphBuilding'
  | 'Completed'
  | 'Failed';

// Labels are locale keys under knowledgeBase:documentDetail.*; callers
// translate them. Unknown backend step names render as raw text.
const STAGE_LABEL_KEYS: Record<ProcessingStage, string> = {
  Pending: 'documentDetail.stage.Pending',
  Loading: 'documentDetail.stage.Loading',
  Splitting: 'documentDetail.stage.Splitting',
  Indexing: 'documentDetail.stage.Indexing',
  GraphBuilding: 'documentDetail.stage.GraphBuilding',
  Completed: 'documentDetail.stage.Completed',
  Failed: 'documentDetail.stage.Failed',
};

const PIPELINE_STEPS: ProcessingStage[] = [
  'Loading',
  'Splitting',
  'Indexing',
  'Completed',
];

export interface PipelineStep {
  stage: ProcessingStage | string;
  label: string;
  status: 'pending' | 'active' | 'done' | 'failed';
}

/** Backend step name → locale key mapping */
const BACKEND_STEP_KEYS: Record<string, string> = {
  DocumentLoaderStep: 'documentDetail.backendStep.DocumentLoaderStep',
  DocumentSplitterStep: 'documentDetail.backendStep.DocumentSplitterStep',
  TokenizerStep: 'documentDetail.backendStep.TokenizerStep',
  TerminologyStep: 'documentDetail.backendStep.TerminologyStep',
  GCStep: 'documentDetail.backendStep.GCStep',
  IndexBuilderStep: 'documentDetail.backendStep.IndexBuilderStep',
  GraphBuilderStep: 'documentDetail.backendStep.GraphBuilderStep',
};

export type StageProgressItem = {
  name: string;
  status: 'pending' | 'running' | 'done' | 'failed';
  startedAt: string | null;
  endedAt: string | null;
};

/**
 * Build pipeline steps from real backend stage progress data.
 * Returns null if no progress data is available (caller should fall back to legacy mode).
 */
export function getPipelineStepsFromProgress(progress: StageProgressItem[]): PipelineStep[] | null {
  if (!progress || progress.length === 0) return null;
  return progress.map((item) => ({
    stage: item.name,
    label: BACKEND_STEP_KEYS[item.name] ?? item.name,
    status: item.status === 'running' ? 'active' : item.status,
  }));
}

/** Legacy fallback: derive pipeline steps from a single stage name. */
export function getPipelineSteps(currentStage: ProcessingStage): PipelineStep[] {
  if (currentStage === 'Pending') {
    return PIPELINE_STEPS.map((s) => ({ stage: s, label: STAGE_LABEL_KEYS[s], status: 'pending' as const }));
  }

  if (currentStage === 'Completed') {
    return PIPELINE_STEPS.map((s) => ({ stage: s, label: STAGE_LABEL_KEYS[s], status: 'done' as const }));
  }

  if (currentStage === 'Failed') {
    return PIPELINE_STEPS.map((s) => ({ stage: s, label: STAGE_LABEL_KEYS[s], status: 'failed' as const }));
  }

  const idx = PIPELINE_STEPS.indexOf(currentStage);
  if (idx === -1) {
    return PIPELINE_STEPS.map((s) => ({ stage: s, label: STAGE_LABEL_KEYS[s], status: 'pending' as const }));
  }

  return PIPELINE_STEPS.map((step, i) => ({
    stage: step,
    label: STAGE_LABEL_KEYS[step],
    status: i < idx ? ('done' as const) : i === idx ? ('active' as const) : ('pending' as const),
  }));
}

/** Returns a locale key when known, otherwise the raw stage text. */
export function getStageLabel(stage: string): string {
  return STAGE_LABEL_KEYS[stage as ProcessingStage] ?? BACKEND_STEP_KEYS[stage] ?? stage;
}

export function isDocumentStageKey(label: string): boolean {
  return label.startsWith('documentDetail.');
}

export function isIngestPolling(status: IngestStatus | undefined): boolean {
  return status === 'Pending' || status === 'Processing';
}

type IngestStatus = import('./contracts').IngestStatus;
