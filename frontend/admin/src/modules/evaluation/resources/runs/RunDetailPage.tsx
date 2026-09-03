import { useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, ExternalLink, RotateCcw, GitCompare } from 'lucide-react';
import { useRunDetail, useRunConfigList, useTriggerRun } from '../configs/hooks';
import { useCaseList, useDatasetList } from '../datasets/hooks';
import { Modal } from '@/shared/ui/Modal';
import { getErrorMessage } from '@/shared/api/errors';
import type { CaseData, RunResultData } from '../../lib/contracts';

export function RunDetailPage() {
  const { t } = useTranslation(['common', 'evaluation']);
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { data: detail, isLoading, error } = useRunDetail(runId ?? '');
  const { data: configs } = useRunConfigList();
  const { data: datasets } = useDatasetList();
  const [selected, setSelected] = useState<RunResultData | null>(null);
  const triggerMutation = useTriggerRun();
  const loadedConfig = configs?.find((item) => String(item.id) === String(detail?.run.configId));
  const { data: cases } = useCaseList(loadedConfig?.datasetId ?? '');

  if (isLoading) return <State text={t('states.loading')} />;
  if (error || !detail) return <State text={getErrorMessage(error) || 'Evaluation run unavailable.'} error />;

  const { run, results } = detail;
  const config = loadedConfig;
  const dataset = datasets?.items.find((item) => String(item.id) === String(config?.datasetId));
  const caseById = new Map((cases ?? []).map((item) => [String(item.id), item]));
  const baseline = params.get('baseline');
  const runAgain = async () => {
    const next = await triggerMutation.mutateAsync(run.configId);
    navigate(`/evaluation/runs/${next.id}?baseline=${encodeURIComponent(run.id)}`);
  };
  const summary = summarize(run.summary, results);

  return (
    <div className="flex flex-col gap-6 p-6">
      <button type="button" onClick={() => navigate('/evaluation/runs')} className="inline-flex items-center gap-2 self-start text-sm text-text-secondary hover:text-primary"><ArrowLeft size={15} /> Evaluation Runs</button>
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div><div className="flex items-center gap-3"><h1 className="font-mono text-lg text-text">Evaluation Run #{run.id}</h1><Status status={run.status} /></div><div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm text-text-secondary"><span>Agent: <strong className="font-medium text-text">{config?.targetType === 'agent' ? config.targetKey : '—'}</strong></span><span>Dataset: <strong className="font-medium text-text">{dataset?.name ?? config?.datasetId ?? '—'}</strong></span><span>Configuration: <strong className="font-medium text-text">{config?.name ?? run.configId}</strong></span></div></div>
        <div className="flex flex-wrap gap-2"><button type="button" onClick={runAgain} disabled={triggerMutation.isPending} className="inline-flex items-center gap-2 bg-primary px-3 py-2 text-sm text-background disabled:opacity-50"><RotateCcw size={14} /> {triggerMutation.isPending ? 'Starting…' : 'Run Again'}</button>{baseline && <button type="button" onClick={() => navigate(`/evaluation/runs/compare?left=${encodeURIComponent(baseline)}&right=${encodeURIComponent(run.id)}`)} className="inline-flex items-center gap-2 border border-border px-3 py-2 text-sm hover:bg-surface-raised"><GitCompare size={14} /> Compare with #{baseline}</button>}{config?.targetType === 'agent' && <button type="button" onClick={() => navigate(`/agents/${encodeURIComponent(config.targetKey)}`)} className="inline-flex items-center gap-2 border border-border px-3 py-2 text-sm hover:bg-surface-raised"><ExternalLink size={14} /> Open Agent</button>}</div>
      </header>
      <section className="grid grid-cols-2 gap-3 md:grid-cols-6" aria-label="Evaluation summary">{[['Average Score', formatScore(summary.avgScore)], ['Passed', formatSummaryValue(summary.passed)], ['Failed', formatSummaryValue(summary.failed)], ['Unknown', formatSummaryValue(summary.unknown)], ['Errors', formatSummaryValue(summary.errors)], ['Total', String(results.length)]].map(([label, value]) => <div key={String(label)} className="border border-border bg-surface px-4 py-3"><div className="text-xs text-text-muted">{label}</div><div className="mt-1 text-lg font-semibold text-text">{value}</div></div>)}</section>
      <section className="overflow-x-auto border border-border bg-surface"><div className="border-b border-border px-4 py-3 text-sm font-semibold text-text">Results <span className="font-normal text-text-muted">({results.length})</span></div><table className="w-full min-w-[720px] text-sm"><thead><tr className="border-b border-border text-left text-text-muted"><th className="px-4 py-3 font-medium">Case</th><th className="px-4 py-3 font-medium">Verdict</th><th className="px-4 py-3 font-medium">Score</th><th className="px-4 py-3 font-medium">Actual Output</th><th className="px-4 py-3 text-right font-medium">Duration</th></tr></thead><tbody>{results.map((result) => <ResultRow key={result.id} result={result} example={caseById.get(String(result.caseId))} onClick={() => setSelected(result)} />)}</tbody></table></section>
      <CaseDrawer result={selected} example={selected ? caseById.get(String(selected.caseId)) : undefined} agentKey={config?.targetType === 'agent' ? config.targetKey : undefined} onClose={() => setSelected(null)} onAgent={() => config?.targetType === 'agent' && navigate(`/agents/${encodeURIComponent(config.targetKey)}`)} onDataset={() => config?.datasetId && navigate(`/evaluation/dataset/${config.datasetId}`)} />
    </div>
  );
}

function ResultRow({ result, example, onClick }: { result: RunResultData; example?: CaseData; onClick: () => void }) { return <tr tabIndex={0} onClick={onClick} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') onClick(); }} className="cursor-pointer border-b border-border-subtle hover:bg-surface-raised focus:bg-surface-raised"><td className="px-4 py-3"><div className="text-text">{example?.inputText?.slice(0, 90) ?? 'Unavailable'}</div><div className="mt-1 font-mono text-xs text-text-muted">#{result.caseId}</div></td><td className={`px-4 py-3 text-xs font-medium ${result.passed === true ? 'text-success' : result.passed === false ? 'text-error' : 'text-text-muted'}`}>{verdict(result)}</td><td className="px-4 py-3">{formatScore(result.overallScore)}</td><td className="max-w-[360px] px-4 py-3 text-text-secondary">{result.actualOutput?.slice(0, 100) || '—'}</td><td className="px-4 py-3 text-right text-text-secondary">{result.durationMs}ms</td></tr>; }

function CaseDrawer({ result, example, agentKey, onClose, onAgent, onDataset }: { result: RunResultData | null; example?: CaseData; agentKey?: string; onClose: () => void; onAgent: () => void; onDataset: () => void }) { return <Modal open={!!result} title={result ? `Case #${result.caseId}` : 'Case'} onClose={onClose} footer={<div className="flex justify-between gap-2"><button type="button" onClick={onDataset} className="text-sm text-primary hover:underline">Open Dataset</button>{agentKey && <button type="button" onClick={onAgent} className="bg-primary px-3 py-2 text-sm text-background">Open Agent</button>}</div>}><div className="space-y-5 text-sm">{result && <><Detail label="Input" value={example?.inputText} /><Detail label="Expected Output" value={example?.expectedOutput} /><Detail label="Actual Output" value={result.actualOutput} /><div className="grid grid-cols-3 gap-3"><Detail label="Verdict" value={verdict(result)} /><Detail label="Overall Score" value={formatScore(result.overallScore)} /><Detail label="Duration" value={`${result.durationMs}ms`} /></div><div><h3 className="mb-2 font-semibold text-text">Metrics</h3><div className="space-y-3">{result.metricResults.map((metric) => <div key={metric.metricName} className="border-t border-border pt-2"><div className="flex justify-between font-medium text-text"><span>{metric.metricName}</span><span>{formatScore(metric.score)} · {metric.passed === null ? '—' : metric.passed ? 'PASS' : 'FAIL'}</span></div><p className="mt-1 whitespace-pre-wrap text-text-secondary">{metric.reasoning ?? '—'}</p></div>)}</div></div>{result.errorMessage && <Detail label="Error" value={result.errorMessage} />}</>}</div></Modal>; }
function Detail({ label, value }: { label: string; value?: string | null }) { return <div><h3 className="mb-1 text-xs font-semibold text-text-muted">{label}</h3><pre className="whitespace-pre-wrap rounded-[2px] border border-border bg-background-subtle p-3 text-text">{value ?? '—'}</pre></div>; }
function summarize(summary: Record<string, unknown>, results: RunResultData[]) { return { avgScore: typeof summary.avgScore === 'number' ? summary.avgScore : results.length && results.every((r) => r.overallScore !== null) ? results.reduce((total, r) => total + (r.overallScore ?? 0), 0) / results.length : null, passed: summary.passed_cases ?? results.filter((r) => r.passed === true).length, failed: summary.failed_cases ?? results.filter((r) => r.passed === false).length, unknown: summary.unknown_cases ?? results.filter((r) => r.passed === null).length, errors: summary.error_count ?? results.filter((r) => !!r.errorMessage).length }; }
function formatScore(value: unknown) { return typeof value === 'number' ? value.toFixed(3) : '—'; }
function formatSummaryValue(value: unknown) { return typeof value === 'number' ? String(value) : '—'; }
function verdict(result: RunResultData) { return result.passed === true ? 'PASS' : result.passed === false ? 'FAIL' : result.errorMessage ? 'ERROR' : 'UNKNOWN'; }
function Status({ status }: { status: string }) { return <span className="rounded-[2px] bg-surface-raised px-2 py-1 text-xs text-text-secondary">{status}</span>; }
function State({ text, error = false }: { text: string; error?: boolean }) { return <div className={`p-6 text-sm ${error ? 'text-error' : 'text-text-muted'}`}>{text}</div>; }
