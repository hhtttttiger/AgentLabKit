import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '@/shared/test/render';
import { RunDetailPage } from './RunDetailPage';
import type { RunConfigData, RunData, RunDetailData } from '../../lib/contracts';

// Snowflake-scale ids: lineage roles must survive as opaque strings.
const RUN_ID = '9007199254740993'; // > Number.MAX_SAFE_INTEGER
const BASELINE_ID = '9007199254740995';
const CANDIDATE_ID = '9007199254741001';

const {
  useRunDetailMock,
  useRunConfigListMock,
  useTriggerRunMock,
} = vi.hoisted(() => ({
  useRunDetailMock: vi.fn(),
  useRunConfigListMock: vi.fn(),
  useTriggerRunMock: vi.fn(),
}));

// vi.mock paths resolve relative to THIS test file (resources/runs/).
vi.mock('../configs/hooks', () => ({
  useRunDetail: useRunDetailMock,
  useRunConfigList: useRunConfigListMock,
  useTriggerRun: useTriggerRunMock,
}));

vi.mock('../datasets/hooks', () => ({
  useCaseList: vi.fn(() => ({ data: [] })),
  useDatasetList: vi.fn(() => ({ data: { items: [], total: 0 } })),
}));

const config: RunConfigData = {
  id: 'cfg-1',
  name: 'Nightly regression',
  datasetId: '9223372036854775807',
  targetType: 'agent',
  targetKey: 'agent.docs',
  metricConfigs: [],
  judgeModelKey: '',
  createdAtUtc: '2026-09-09T00:00:00Z',
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
  results: [],
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
      </Routes>
    </MemoryRouter>,
  );
}

describe('Evaluation RunDetailPage re-evaluation continuity', () => {
  let triggerMutateAsync: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    useRunDetailMock.mockReturnValue({ data: detail, isLoading: false, error: null });
    useRunConfigListMock.mockReturnValue({ data: [config] });
    triggerMutateAsync = vi.fn().mockResolvedValue({
      id: CANDIDATE_ID,
      configId: config.id,
      status: 'pending',
      startedAtUtc: null,
      completedAtUtc: null,
      summary: {},
      createdAtUtc: '2026-09-10T01:00:00Z',
    } satisfies RunData);
    useTriggerRunMock.mockReturnValue({ mutateAsync: triggerMutateAsync, isPending: false });
  });

  it('JC-04: Run Again reuses the config and lands on the candidate with this run as baseline', async () => {
    renderPage();

    fireEvent.click(screen.getByRole('button', { name: 'Run Again' }));
    await waitFor(() => expect(triggerMutateAsync).toHaveBeenCalledWith(config.id));

    await waitFor(() => {
      expect(screen.getByTestId('location')).toHaveTextContent(
        `/evaluation/runs/${CANDIDATE_ID}?baseline=${RUN_ID}`,
      );
    });
  });

  it('JC-04: Compare keeps the journey roles — baseline left, candidate right', () => {
    renderPage(`?baseline=${BASELINE_ID}`);

    fireEvent.click(screen.getByRole('button', { name: `Compare with baseline #${BASELINE_ID}` }));
    expect(screen.getByTestId('location')).toHaveTextContent(
      `/evaluation/runs/compare?left=${BASELINE_ID}&right=${RUN_ID}`,
    );
  });

  it('JC-04: without journey context there is no inferred baseline to compare against', () => {
    renderPage();

    expect(screen.queryByRole('button', { name: /Compare with baseline/ })).not.toBeInTheDocument();
  });
});
