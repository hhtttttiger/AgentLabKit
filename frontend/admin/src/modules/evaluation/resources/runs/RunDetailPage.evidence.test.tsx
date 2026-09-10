import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { fireEvent, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '@/shared/test/render';
import { switchTestLanguage } from '@/shared/test/setup';
import { RunDetailPage } from './RunDetailPage';
import type { MetricResultData, RunConfigData, RunData, RunDetailData, RunResultData } from '../../lib/contracts';

const RUN_ID = '9007199254740993';

const {
  useRunDetailMock,
  useRunConfigListMock,
  useTriggerRunMock,
  useCaseListMock,
  useDatasetListMock,
} = vi.hoisted(() => ({
  useRunDetailMock: vi.fn(),
  useRunConfigListMock: vi.fn(),
  useTriggerRunMock: vi.fn(),
  useCaseListMock: vi.fn(),
  useDatasetListMock: vi.fn(),
}));

vi.mock('../configs/hooks', () => ({
  useRunDetail: useRunDetailMock,
  useRunConfigList: useRunConfigListMock,
  useTriggerRun: useTriggerRunMock,
}));

vi.mock('../datasets/hooks', () => ({
  useCaseList: useCaseListMock,
  useDatasetList: useDatasetListMock,
}));

const config: RunConfigData = {
  id: 'cfg-1',
  name: 'Nightly regression',
  datasetId: '1',
  targetType: 'agent',
  targetKey: 'agent.docs',
  metricConfigs: [],
  judgeModelKey: '',
  createdAtUtc: '2026-09-10T00:00:00Z',
};

function metric(overrides: Partial<MetricResultData>): MetricResultData {
  return {
    metricName: 'faithfulness',
    score: null,
    reasoning: null,
    passed: null,
    reason: null,
    evidence: null,
    ...overrides,
  };
}

function result(overrides: Partial<RunResultData> = {}): RunResultData {
  return {
    id: 'res-1',
    runId: RUN_ID,
    caseId: 'case-1',
    actualOutput: 'Tuesday 03:00 UTC.',
    metricResults: [],
    overallScore: null,
    passed: null,
    errorMessage: null,
    durationMs: 12,
    candidateRunId: 'candidate-run-hex',
    candidateTraceId: 'candidate-trace-hex',
    ...overrides,
  };
}

function renderPage(detailData: RunDetailData) {
  useRunDetailMock.mockReturnValue({ data: detailData, isLoading: false, error: null });

  function LocationProbe() {
    const location = useLocation();
    return <div data-testid="location">{location.pathname}</div>;
  }

  return renderWithQueryClient(
    <MemoryRouter initialEntries={[`/evaluation/runs/${RUN_ID}`]}>
      <Routes>
        <Route path="/evaluation/runs/:runId" element={<><RunDetailPage /><LocationProbe /></>} />
        <Route path="/runs/:runId" element={<LocationProbe />} />
        <Route path="/traces/:traceId" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('Evaluation retrieval evidence surface', () => {
  beforeEach(async () => {
    await switchTestLanguage('en-US');
    useRunConfigListMock.mockReturnValue({ data: [config] });
    useCaseListMock.mockReturnValue({ data: [] });
    useDatasetListMock.mockReturnValue({ data: { items: [], total: 0 } });
    useTriggerRunMock.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
  });

  it('shows the bounded retrieval summary when evidence was used', () => {
    renderPage({
      run: { id: RUN_ID, configId: config.id, status: 'completed', startedAtUtc: null, completedAtUtc: null, summary: {}, createdAtUtc: '2026-09-10T00:00:00Z' } satisfies RunData,
      results: [result({
        metricResults: [metric({
          score: 0.8, passed: null,
          evidence: { availability: 'available', attempts: 2, successfulAttempts: 1, contextsUsed: 3, reason: null },
        })],
      })],
    });

    fireEvent.click(screen.getByText('Tuesday 03:00 UTC.'));
    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByText('Retrieval evidence')).toBeInTheDocument();
    expect(within(dialog).getByText('2 retrieval attempt(s) · 1 successful · 3 context(s) used')).toBeInTheDocument();
  });

  it('says no retrieval occurred instead of showing an empty summary', () => {
    renderPage({
      run: { id: RUN_ID, configId: config.id, status: 'completed', startedAtUtc: null, completedAtUtc: null, summary: {}, createdAtUtc: '2026-09-10T00:00:00Z' } satisfies RunData,
      results: [result({
        metricResults: [metric({
          reason: 'no_retrieval_evidence',
          evidence: { availability: 'not_applicable', attempts: 0, successfulAttempts: 0, contextsUsed: 0, reason: null },
        })],
      })],
    });

    fireEvent.click(screen.getByText('Tuesday 03:00 UTC.'));
    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByText('No retrieval occurred for this run')).toBeInTheDocument();
  });

  it('says evidence is unavailable when the candidate trace could not be read', () => {
    renderPage({
      run: { id: RUN_ID, configId: config.id, status: 'completed', startedAtUtc: null, completedAtUtc: null, summary: {}, createdAtUtc: '2026-09-10T00:00:00Z' } satisfies RunData,
      results: [result({
        metricResults: [metric({
          reason: 'trace_unavailable',
          evidence: { availability: 'unavailable', attempts: 0, successfulAttempts: 0, contextsUsed: 0, reason: 'trace_unavailable' },
        })],
      })],
    });

    fireEvent.click(screen.getByText('Tuesday 03:00 UTC.'));
    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByText('Retrieval evidence unavailable')).toBeInTheDocument();
    expect(within(dialog).getByText('trace_unavailable')).toBeInTheDocument();
  });

  it('links the candidate Run identity', () => {
    renderPage({
      run: { id: RUN_ID, configId: config.id, status: 'completed', startedAtUtc: null, completedAtUtc: null, summary: {}, createdAtUtc: '2026-09-10T00:00:00Z' } satisfies RunData,
      results: [result()],
    });

    fireEvent.click(screen.getByText('Tuesday 03:00 UTC.'));
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Open Run' }));
    expect(screen.getByTestId('location')).toHaveTextContent('/runs/candidate-run-hex');
  });

  it('links the candidate Trace identity', () => {
    renderPage({
      run: { id: RUN_ID, configId: config.id, status: 'completed', startedAtUtc: null, completedAtUtc: null, summary: {}, createdAtUtc: '2026-09-10T00:00:00Z' } satisfies RunData,
      results: [result()],
    });

    fireEvent.click(screen.getByText('Tuesday 03:00 UTC.'));
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Inspect Trace' }));
    expect(screen.getByTestId('location')).toHaveTextContent('/traces/candidate-trace-hex');
  });

  it('omits evidence UI for legacy results without evidence', () => {
    renderPage({
      run: { id: RUN_ID, configId: config.id, status: 'completed', startedAtUtc: null, completedAtUtc: null, summary: {}, createdAtUtc: '2026-09-10T00:00:00Z' } satisfies RunData,
      results: [result({ candidateRunId: null, candidateTraceId: null })],
    });

    fireEvent.click(screen.getByText('Tuesday 03:00 UTC.'));
    const dialog = screen.getByRole('dialog');
    expect(within(dialog).queryByText('Retrieval evidence')).not.toBeInTheDocument();
    expect(within(dialog).queryByRole('button', { name: 'Open Run' })).not.toBeInTheDocument();
  });
});
