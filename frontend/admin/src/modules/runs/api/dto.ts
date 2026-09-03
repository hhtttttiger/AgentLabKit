/** Public Run and evaluation-comparison DTOs from the FastAPI adapters. */

export interface RunListDto {
  items: RunDetailDto[];
  total: number;
}

export interface RunDetailDto {
  runId: string;
  traceId: string | null;
  status: string;
  targetType: string | null;
  targetKey: string | null;
  targetVersion: string | null;
  input: unknown;
  output: unknown;
  startedAt: string | null;
  completedAt: string | null;
  durationMs: number | null;
  sessionId: string | null;
  errorCode: string | null;
  errorMessage: string | null;
  metadata: Record<string, unknown>;
}

export interface ReplayRunDto {
  sourceRunId: string;
  run: RunDetailDto;
}

export interface CaptureRunRequest {
  datasetId: number;
  expectedOutput?: unknown;
  metadata?: Record<string, unknown>;
}

export interface CaptureRunResponse {
  datasetId: string;
  sourceRunId: string;
  exampleId: string;
}

export interface CompareEvaluationRunsRequest {
  leftRunId: string;
  rightRunId: string;
}

export interface EvaluationResultDto {
  exampleId: string;
  score: number | null;
  passed: boolean | null;
  message: string | null;
  details: Record<string, unknown>;
  durationMs: number;
}

export interface EvaluationExampleComparisonDto {
  exampleId: string;
  classification: string;
  left: EvaluationResultDto | null;
  right: EvaluationResultDto | null;
}

export interface CompareEvaluationRunsDto {
  leftRunId: string;
  rightRunId: string;
  datasetId: string;
  matchedCount: number;
  leftOnlyCount: number;
  rightOnlyCount: number;
  examples: EvaluationExampleComparisonDto[];
}
