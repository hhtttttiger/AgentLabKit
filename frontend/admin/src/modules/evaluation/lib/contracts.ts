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
  judgeModelBindingKey: string;
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

export interface RunResultData {
  id: string;
  runId: string;
  caseId: string;
  actualOutput: string;
  metricResults: { metricName: string; score: number; reasoning: string | null; passed: boolean | null }[];
  overallScore: number;
  errorMessage: string | null;
  durationMs: number;
}

export interface RunDetailData {
  run: RunData;
  results: RunResultData[];
}
