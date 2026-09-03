import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { useRunConfigList, useRunDetail } from '../configs/hooks';
import { useDatasetList, useCaseList } from '../datasets/hooks';
import { compareEvaluationRuns } from '../configs/api';
import { targetIdentity } from './presentation';

export function RunComparePage() {
  const [params] = useSearchParams();
  const baselineId = params.get('left') ?? params.get('baseline') ?? '';
  const candidateId = params.get('right') ?? params.get('candidate') ?? '';
  const query = useQuery({ queryKey: ['evaluation', 'compare', baselineId, candidateId], queryFn: () => compareEvaluationRuns({ leftRunId: baselineId, rightRunId: candidateId }), enabled: !!baselineId && !!candidateId });
  const { data: configs } = useRunConfigList();
  const { data: baselineRun } = useRunDetail(baselineId);
  const { data: candidateRun } = useRunDetail(candidateId);
  const { data: datasets } = useDatasetList();
  const datasetId = query.data?.datasetId ?? configs?.find((config) => String(config.id) === String(baselineRun?.run.configId))?.datasetId ?? '';
  const { data: cases } = useCaseList(datasetId);
  const caseById = new Map((cases ?? []).map((item) => [String(item.id), item]));

  if (!baselineId || !candidateId) return <State text="Select two evaluation run IDs to compare." />;
  if (query.isLoading) return <State text="Loading comparison…" />;
  if (query.error || !query.data) return <State text="Evaluation runs are not comparable." error />;
  const result = query.data;
  const counts = result.examples.reduce<Record<string, number>>((acc, item) => { acc[item.classification] = (acc[item.classification] ?? 0) + 1; return acc; }, {});
  const dataset = datasets?.items.find((item) => String(item.id) === String(result.datasetId));
  const baselineConfig = configs?.find((config) => String(config.id) === String(baselineRun?.run.configId));
  const candidateConfig = configs?.find((config) => String(config.id) === String(candidateRun?.run.configId));
  const runIdentity = (run: typeof baselineRun, config: typeof baselineConfig) => ({ ...targetIdentity(config?.targetType, config?.targetKey ?? run?.run.configId), configName: config?.name ?? run?.run.configId ?? '—' });
  const baselineIdentity = runIdentity(baselineRun, baselineConfig);
  const candidateIdentity = runIdentity(candidateRun, candidateConfig);

  return <div className="space-y-5 p-6"><header><h1 className="text-lg font-semibold text-text">Evaluation Compare</h1><p className="mt-1 text-sm text-text-secondary">{dataset?.name ?? `Dataset ${result.datasetId}`} · {result.matchedCount} matched · {result.leftOnlyCount} baseline only · {result.rightOnlyCount} candidate only</p><div className="mt-4 grid gap-3 md:grid-cols-2"><RunIdentity title="Baseline" runId={baselineId} identity={baselineIdentity} /><RunIdentity title="Candidate" runId={candidateId} identity={candidateIdentity} /></div></header><div className="grid grid-cols-3 gap-3">{Object.entries(counts).map(([classification, count]) => <div key={classification} className="border border-border bg-surface px-4 py-3"><div className="text-xs text-text-muted">{classification}</div><div className="mt-1 text-lg font-semibold text-text">{count}</div></div>)}</div><div className="overflow-x-auto border border-border bg-surface"><table className="w-full min-w-[680px] text-sm"><thead><tr className="border-b border-border text-left text-text-muted"><th className="p-3 font-medium">Case</th><th className="p-3 font-medium">Baseline · #{baselineId}</th><th className="p-3 font-medium">Candidate · #{candidateId}</th><th className="p-3 font-medium">Change</th></tr></thead><tbody>{result.examples.map((example) => <tr key={example.exampleId} className="border-b border-border-subtle"><td className="p-3"><div className="text-text">{caseById.get(String(example.exampleId))?.inputText?.slice(0, 100) ?? 'Unavailable'}</div><div className="mt-1 font-mono text-xs text-text-muted">#{example.exampleId}</div></td><td className="p-3">{formatResult(example.left)}</td><td className="p-3">{formatResult(example.right)}</td><td className="p-3 font-medium text-text">{example.classification}</td></tr>)}</tbody></table></div></div>;
}

function RunIdentity({ title, runId, identity }: { title: string; runId: string; identity: { key: string | number; label: string; configName: string } }) {
  return <section className="border border-border bg-surface px-4 py-3"><h2 className="text-xs font-semibold uppercase tracking-wide text-text-muted">{title}</h2><p className="mt-1 font-mono text-sm text-text">Run #{runId}</p><dl className="mt-2 space-y-1 text-sm"><div><dt className="inline text-text-muted">{identity.label}: </dt><dd className="inline font-medium text-text">{identity.key}</dd></div><div><dt className="inline text-text-muted">Configuration: </dt><dd className="inline text-text">{identity.configName}</dd></div></dl></section>;
}
export function formatResult(result: { score: number | null; passed: boolean | null } | null) { return result ? `${result.score ?? '—'} / ${result.passed === null ? '—' : result.passed ? 'pass' : 'fail'}` : '—'; }
function State({ text, error = false }: { text: string; error?: boolean }) { return <div className={`p-6 text-sm ${error ? 'text-error' : 'text-text-muted'}`}>{text}</div>; }
