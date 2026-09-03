import { describe, expect, it } from 'vitest';
import type { RunResultData } from '../../lib/contracts';
import { canCompare, canRunAgain, summarize, targetIdentity, targetLabel } from './presentation';

const result = (overrides: Partial<RunResultData>): RunResultData => ({
  id: 'result', runId: '1', caseId: 'case', actualOutput: '', metricResults: [],
  overallScore: null, passed: null, errorMessage: null, durationMs: 0, ...overrides,
});

describe('evaluation run lifecycle presentation', () => {
  it('only offers actions for authoritative lifecycle states', () => {
    expect(canRunAgain('running')).toBe(false);
    expect(canRunAgain('pending')).toBe(false);
    expect(canRunAgain('completed')).toBe(true);
    expect(canCompare('running', '31')).toBe(false);
    expect(canCompare('completed', '31')).toBe(true);
  });

  it('keeps unknown and error results exclusive', () => {
    const summary = summarize({}, [result({}), result({ errorMessage: 'boom' })]);
    expect(summary.unknown).toBe(1);
    expect(summary.errors).toBe(1);
  });

  it('does not turn nullable scores into zero and labels RAG targets', () => {
    expect(summarize({}, [result({ overallScore: null })]).avgScore).toBeNull();
    expect(targetLabel('rag_pipeline')).toBe('RAG Pipeline');
    expect(targetLabel('agent')).toBe('Agent');
    expect(targetIdentity('agent', 'agent-a')).toEqual({ label: 'Agent', key: 'agent-a' });
    expect(targetIdentity('rag_pipeline', 'pipeline-b')).toEqual({ label: 'RAG Pipeline', key: 'pipeline-b' });
  });
});
