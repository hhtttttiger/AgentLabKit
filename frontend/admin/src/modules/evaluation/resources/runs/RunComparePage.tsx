import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { compareEvaluationRuns } from '@/modules/evaluation/resources/configs/api';

/** Comparison is evaluation-owned and keyed by DatasetExample.example_id. */
export function RunComparePage() {
  const [params] = useSearchParams();
  const leftRunId = params.get('left') ?? params.get('baseline') ?? '';
  const rightRunId = params.get('right') ?? params.get('candidate') ?? '';
  const query = useQuery({
    queryKey: ['evaluation', 'compare', leftRunId, rightRunId],
    queryFn: () => compareEvaluationRuns({ leftRunId, rightRunId }),
    enabled: !!leftRunId && !!rightRunId,
  });

  if (!leftRunId || !rightRunId) return <State text="Select two evaluation run IDs to compare." />;
  if (query.isLoading) return <State text="Loading comparison…" />;
  if (query.error || !query.data) return <State text="Evaluation runs are not comparable." error />;

  const result = query.data;
  return <div className="space-y-4 p-6">
    <h1 className="text-lg font-semibold text-text">Evaluation comparison</h1>
    <p className="text-sm text-text-secondary">{result.matchedCount} matched · {result.leftOnlyCount} left-only · {result.rightOnlyCount} right-only</p>
    <div className="overflow-x-auto border border-border bg-surface"><table className="w-full text-sm"><thead><tr className="border-b border-border text-left"><th className="p-3">Example ID</th><th className="p-3">Left</th><th className="p-3">Right</th><th className="p-3">Verdict</th></tr></thead><tbody>{result.examples.map((example) => <tr key={example.exampleId} className="border-b border-border-subtle"><td className="p-3 font-mono">{example.exampleId}</td><td className="p-3">{formatResult(example.left)}</td><td className="p-3">{formatResult(example.right)}</td><td className="p-3">{example.classification}</td></tr>)}</tbody></table></div>
  </div>;
}
export function formatResult(result: { score: number | null; passed: boolean | null } | null) { return result ? `${result.score ?? '—'} / ${result.passed === null ? '—' : result.passed ? 'pass' : 'fail'}` : '—'; }
function State({ text, error = false }: { text: string; error?: boolean }) { return <div className={`p-6 text-sm ${error ? 'text-error' : 'text-text-muted'}`}>{text}</div>; }
