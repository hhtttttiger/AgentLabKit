export interface DatasetData {
  id: string;
  name: string;
  description: string | null;
  tags: string[];
  caseCount: number;
  isActive: boolean;
  createdAtUtc: string;
  updatedAtUtc: string;
}

export interface CaseData {
  id: string;
  datasetId: string;
  caseIndex: number;
  inputText: string;
  expectedOutput: string | null;
  context: string[];
  tags: string[];
}

export interface RunConfigData {
  id: string;
  name: string;
  datasetId: string;
  targetType: string;
  targetKey: string;
  metricConfigs: Record<string, unknown>[];
  judgeModelKey: string;
  createdAtUtc: string;
}

export interface RunData {
  id: string;
  configId: string;
  status: string;
  startedAtUtc: string | null;
  completedAtUtc: string | null;
  summary: Record<string, unknown>;
  createdAtUtc: string;
}

export interface RetrievalEvidenceSummary {
  availability: 'available' | 'not_applicable' | 'unavailable';
  attempts: number;
  successfulAttempts: number;
  contextsUsed: number;
  reason: string | null;
}

export interface MetricResultData {
  metricName: string;
  score: number | null;
  reasoning: string | null;
  passed: boolean | null;
  /** Machine-readable unavailable reason (e.g. missing_reference). */
  reason: string | null;
  /** Bounded retrieval-evidence summary the metric consumed. */
  evidence: RetrievalEvidenceSummary | null;
}

export interface RunResultData {
  id: string;
  runId: string;
  caseId: string;
  actualOutput: string;
  metricResults: MetricResultData[];
  overallScore: number | null;
  passed: boolean | null;
  errorMessage: string | null;
  durationMs: number;
  /** Runtime-owned candidate execution identity (Open Run / Inspect Trace). */
  candidateRunId: string | null;
  candidateTraceId: string | null;
}

export interface RunDetailData {
  run: RunData;
  results: RunResultData[];
}
