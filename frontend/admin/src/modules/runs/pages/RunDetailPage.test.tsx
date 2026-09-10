import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '@/shared/test/render';
import { RunDetailPage } from './RunDetailPage';
import type { RunDetail } from '../types';

// Snowflake-scale ids: every assertion below proves identity stays a string.
const RUN_ID = '9007199254740993'; // > Number.MAX_SAFE_INTEGER
const DATASET_ID = '9223372036854775807'; // > Number.MAX_SAFE_INTEGER

const {
  useRunDetailMock,
  useRunTraceMock,
  useCaptureRunMock,
  useDatasetListMock,
  useCreateDatasetMock,
  useToastMock,
} = vi.hoisted(() => ({
  useRunDetailMock: vi.fn(),
  useRunTraceMock: vi.fn(),
  useCaptureRunMock: vi.fn(),
  useDatasetListMock: vi.fn(),
  useCreateDatasetMock: vi.fn(),
  useToastMock: vi.fn(),
}));

vi.mock('../hooks', () => ({
  useRunDetail: useRunDetailMock,
  useRunTrace: useRunTraceMock,
  useCaptureRun: useCaptureRunMock,
}));

vi.mock('@/modules/evaluation/resources/datasets/hooks', () => ({
  useDatasetList: useDatasetListMock,
  useCreateDataset: useCreateDatasetMock,
}));

vi.mock('@/shared/ui/Toast', () => ({
  useToast: useToastMock,
}));

vi.mock('@/shared/agent-trace/AgentTraceView', () => ({
  AgentTraceView: () => null,
}));

const run: RunDetail = {
  id: RUN_ID,
  agentKey: 'agent.docs',
  agentVersion: '3',
  status: 'completed',
  durationMs: 1200,
  costUsd: null,
  evaluationScore: null,
  startedAt: '2026-09-10T00:00:00Z',
  completedAt: '2026-09-10T00:00:01Z',
  errorMessage: null,
  modelKey: null,
  sessionId: null,
  traceId: null,
  input: 'hello',
  output: 'hi',
  totalTokens: null,
  metadata: {},
};

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname}{location.search}</div>;
}

function renderPage() {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={[`/runs/${RUN_ID}`]}>
      <Routes>
        <Route path="/runs/:runId" element={<RunDetailPage />} />
        <Route path="/evaluation/dataset/:datasetId" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('RunDetailPage capture continuity', () => {
  let captureMutateAsync: ReturnType<typeof vi.fn>;
  let createDatasetMutateAsync: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    useRunDetailMock.mockReturnValue({ data: run, isLoading: false, error: null });
    useRunTraceMock.mockReturnValue({ data: null, isLoading: false, error: null });
    useToastMock.mockReturnValue({ toast: vi.fn() });
    captureMutateAsync = vi.fn().mockResolvedValue({ datasetId: DATASET_ID, sourceRunId: RUN_ID, exampleId: '424242' });
    useCaptureRunMock.mockReturnValue({ mutateAsync: captureMutateAsync, isPending: false, error: null, reset: vi.fn() });
    createDatasetMutateAsync = vi.fn().mockResolvedValue({
      id: DATASET_ID,
      name: 'Fresh Set',
      description: null,
      tags: [],
      caseCount: 0,
      isActive: true,
      createdAtUtc: '2026-09-10T00:00:00Z',
      updatedAtUtc: '2026-09-10T00:00:00Z',
    });
    useCreateDatasetMock.mockReturnValue({ mutateAsync: createDatasetMutateAsync, isPending: false, error: null, reset: vi.fn() });
    useDatasetListMock.mockReturnValue({
      data: {
        items: [{ id: DATASET_ID, name: 'Regression Set', description: null, tags: [], caseCount: 3, isActive: true, createdAtUtc: '2026-09-09T00:00:00Z', updatedAtUtc: '2026-09-09T00:00:00Z' }],
        total: 1,
      },
    });
  });

  const openCaptureModal = async () => {
    renderPage();
    fireEvent.click(screen.getByRole('button', { name: 'Add to Dataset' }));
    const dialog = await screen.findByRole('dialog');
    fireEvent.change(within(dialog).getByRole('combobox'), { target: { value: DATASET_ID } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Add to Dataset' }));
    return screen.findByRole('status');
  };

  it('JC-01: capture success names the dataset and offers the exact Open Dataset target', async () => {
    const banner = await openCaptureModal();
    await waitFor(() => expect(banner).toHaveTextContent('Added to Regression Set.'));

    fireEvent.click(within(banner).getByRole('button', { name: 'Open Dataset' }));
    expect(screen.getByTestId('location')).toHaveTextContent(`/evaluation/dataset/${DATASET_ID}`);
  });

  it('JC-01: capture success offers Evaluate Dataset with the evaluate deep link', async () => {
    const banner = await openCaptureModal();
    await waitFor(() => expect(banner).toHaveTextContent('Added to Regression Set.'));

    fireEvent.click(within(banner).getByRole('button', { name: 'Evaluate Dataset' }));
    expect(screen.getByTestId('location')).toHaveTextContent(`/evaluation/dataset/${DATASET_ID}?evaluate=1`);
  });

  it('JC-01: capture request carries the dataset id as a string and never invents an expected output', async () => {
    await openCaptureModal();
    await waitFor(() => expect(captureMutateAsync).toHaveBeenCalled());

    expect(captureMutateAsync).toHaveBeenCalledWith({
      runId: RUN_ID,
      request: { datasetId: DATASET_ID },
    });
    const request = captureMutateAsync.mock.calls[0][0].request;
    expect(request.datasetId).toBe(DATASET_ID);
    expect('expectedOutput' in request).toBe(false);
  });

  it('JC-01: with no datasets the modal creates one inline and continues into it', async () => {
    useDatasetListMock.mockReturnValue({ data: { items: [], total: 0 } });

    renderPage();
    fireEvent.click(screen.getByRole('button', { name: 'Add to Dataset' }));
    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveTextContent('No datasets yet.');

    fireEvent.change(within(dialog).getByLabelText('New dataset name'), { target: { value: 'Fresh Set' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Create Dataset' }));
    await waitFor(() => expect(createDatasetMutateAsync).toHaveBeenCalledWith({ name: 'Fresh Set' }));
    expect(await within(dialog).findByText('Created “Fresh Set”. This run will be added to it.')).toBeInTheDocument();

    const submit = within(dialog).getByRole('button', { name: 'Add to Dataset' });
    expect(submit).toBeEnabled();
    fireEvent.click(submit);

    // The modal also renders a role="status" line after inline creation, so
    // anchor on the banner text: the modal and banner never coexist.
    const bannerText = await screen.findByText('Added to Fresh Set.', { exact: false });
    expect(bannerText.closest('[role="status"]')).not.toBeNull();
    expect(captureMutateAsync).toHaveBeenCalledWith({ runId: RUN_ID, request: { datasetId: DATASET_ID } });
  });
});
