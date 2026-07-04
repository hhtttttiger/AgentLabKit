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

const STAGE_LABELS: Record<ProcessingStage, string> = {
  Pending: '等待中',
  Loading: '加载文件',
  Splitting: '文本切分',
  Indexing: '构建索引',
  GraphBuilding: '图谱构建',
  Completed: '已完成',
  Failed: '失败',
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

/** Backend step name → Chinese label mapping */
const BACKEND_STEP_LABELS: Record<string, string> = {
  DocumentLoaderStep: '加载文件',
  DocumentSplitterStep: '文本切分',
  TokenizerStep: '分词处理',
  TerminologyStep: '术语匹配',
  GCStep: '内存回收',
  IndexBuilderStep: '构建索引',
  GraphBuilderStep: '图谱构建',
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
    label: BACKEND_STEP_LABELS[item.name] ?? item.name,
    status: item.status === 'running' ? 'active' : item.status,
  }));
}

/** Legacy fallback: derive pipeline steps from a single stage name. */
export function getPipelineSteps(currentStage: ProcessingStage): PipelineStep[] {
  if (currentStage === 'Pending') {
    return PIPELINE_STEPS.map((s) => ({ stage: s, label: STAGE_LABELS[s], status: 'pending' as const }));
  }

  if (currentStage === 'Completed') {
    return PIPELINE_STEPS.map((s) => ({ stage: s, label: STAGE_LABELS[s], status: 'done' as const }));
  }

  if (currentStage === 'Failed') {
    return PIPELINE_STEPS.map((s) => ({ stage: s, label: STAGE_LABELS[s], status: 'failed' as const }));
  }

  const idx = PIPELINE_STEPS.indexOf(currentStage);
  if (idx === -1) {
    return PIPELINE_STEPS.map((s) => ({ stage: s, label: STAGE_LABELS[s], status: 'pending' as const }));
  }

  return PIPELINE_STEPS.map((step, i) => ({
    stage: step,
    label: STAGE_LABELS[step],
    status: i < idx ? ('done' as const) : i === idx ? ('active' as const) : ('pending' as const),
  }));
}

export function getStageLabel(stage: string): string {
  return STAGE_LABELS[stage as ProcessingStage] ?? BACKEND_STEP_LABELS[stage] ?? stage;
}

export function isIngestPolling(status: IngestStatus | undefined): boolean {
  return status === 'Pending' || status === 'Processing';
}

type IngestStatus = import('./contracts').IngestStatus;
