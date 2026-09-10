import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { fireEvent, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '@/shared/test/render';
import { RunDetailPage } from './RunDetailPage';
import type { RunConfigData, RunData, RunDetailData, RunResultData } from '../../lib/contracts';

// Snowflake-scale ids: roles and targets must survive as opaque strings.
const RUN_ID = '9007199254740993'; // > Number.MAX_SAFE_INTEGER
const DATASET_ID = '9223372036854775807';

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

// vi.mock paths resolve relative to THIS test file (resources/runs/).
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
  datasetId: DATASET_ID,
  targetType: 'agent',
  targetKey: 'agent.docs',
  metricConfigs: [],
  judgeModelKey: '',
  createdAtUtc: '2026-09-09T00:00:00Z',
};

const result: RunResultData = {
  id: 'res-1',
  runId: RUN_ID,
  caseId: 'case-1',
  actualOutput: 'Paris.',
  metricResults: [],
  overallScore: 0.42,
  passed: false,
  errorMessage: null,
  durationMs: 15,
};

const detail: RunDetailData = {
  run: {
    id: RUN_ID,
    configId: config.id,
    status: 'completed',
    startedAtUtc: '2026-09-10T00:00:00Z',
    completedAtUtc: '2026-09-10T00:00:05Z',
    summary: {},
    createdAtUtc: '2026-09-10T00:00:00Z',
  } satisfies RunData,
  results: [result],
};

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname}{location.search}</div>;
}

function renderPage(search = '') {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={[`/evaluation/runs/${RUN_ID}${search}`]}>
      <Routes>
        {/* Probe rides along inside the run route: Run Again navigates to
            another run id, which still matches /runs/:runId. */}
        <Route path="/evaluation/runs/:runId" element={<><RunDetailPage /><LocationProbe /></>} />
        <Route path="/evaluation/runs/compare" element={<LocationProbe />} />
        <Route path="/agents/:agentKey" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('Evaluation RunDetailPage continuity', () => {
  beforeEach(() => {
    useRunDetailMock.mockReturnValue({ data: detail, isLoading: false, error: null });
    useRunConfigListMock.mockReturnValue({ data: [config] });
    useCaseListMock.mockReturnValue({ data: [] });
    useDatasetListMock.mockReturnValue({ data: { items: [], total: 0 } });
    useTriggerRunMock.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
  });

  it('JC-03: Open Agent targets the exact agent and carries the evaluation identity back', () => {
    renderPage();

    fireEvent.click(screen.getByRole('button', { name: 'Open Agent' }));
    expect(screen.getByTestId('location')).toHaveTextContent(`/agents/agent.docs?returnEvaluation=${RUN_ID}`);
  });

  it('JC-03: the failure drawer Open Agent carries the same evaluation identity', () => {
    renderPage();

    fireEvent.click(screen.getByText('Paris.'));
    const dialog = screen.getByRole('dialog');
    fireEvent.click(within(dialog).getByRole('button', { name: 'Open Agent' }));

    expect(screen.getByTestId('location')).toHaveTextContent(`/agents/agent.docs?returnEvaluation=${RUN_ID}`);
  });
});
