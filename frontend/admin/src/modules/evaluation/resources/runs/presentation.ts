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
  const hasTotal = typeof summary.total_cases === 'number';
  return {
    avgScore: typeof summary.avgScore === 'number' ? summary.avgScore : results.length > 0 && results.every((r) => r.overallScore !== null) ? results.reduce((total, r) => total + (r.overallScore ?? 0), 0) / results.length : null,
    passed: typeof summary.passed_cases === 'number' ? summary.passed_cases : results.filter((r) => r.passed === true).length,
    failed: typeof summary.failed_cases === 'number' ? summary.failed_cases : results.filter((r) => r.passed === false && !r.errorMessage).length,
    unknown: results.filter((r) => r.passed === null && !r.errorMessage).length,
    errors: results.filter((r) => Boolean(r.errorMessage)).length,
    total: hasTotal ? summary.total_cases : null,
  };
}
