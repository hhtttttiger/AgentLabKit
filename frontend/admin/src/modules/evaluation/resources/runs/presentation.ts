import type { RunResultData } from '../../lib/contracts';

export function canRunAgain(status: string) {
  return status !== 'running' && status !== 'pending';
}

export function canCompare(status: string, baselineId: string | null) {
  return status === 'completed' && Boolean(baselineId);
}

export function targetLabel(targetType?: string) {
  return targetType === 'rag_pipeline' ? 'RAG Pipeline' : 'Agent';
}

export function targetIdentity(targetType: string | undefined, targetKey: string | number | undefined) {
  return { label: targetLabel(targetType), key: targetKey ?? '—' };
}

export function summarize(summary: Record<string, unknown>, results: RunResultData[]) {
  // Summary JSON keys are the snake_case storage contract (avg_score / total_cases).
  // Unavailable scores (null) never enter the average and never become 0.
  const hasTotal = typeof summary.total_cases === 'number';
  const availableScores = results
    .map((r) => r.overallScore)
    .filter((score): score is number => score !== null);
  const fallbackAvg = availableScores.length > 0
    ? availableScores.reduce((total, score) => total + score, 0) / availableScores.length
    : null;
  return {
    avgScore: typeof summary.avg_score === 'number' ? summary.avg_score : fallbackAvg,
    passed: typeof summary.passed_cases === 'number' ? summary.passed_cases : results.filter((r) => r.passed === true).length,
    failed: typeof summary.failed_cases === 'number' ? summary.failed_cases : results.filter((r) => r.passed === false && !r.errorMessage).length,
    unknown: results.filter((r) => r.passed === null && !r.errorMessage).length,
    errors: results.filter((r) => Boolean(r.errorMessage)).length,
    total: hasTotal ? summary.total_cases : null,
  };
}
