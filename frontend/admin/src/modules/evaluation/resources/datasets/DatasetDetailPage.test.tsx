import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '@/shared/test/render';
import { DatasetDetailPage } from './DatasetDetailPage';
import type { DatasetData } from '../../lib/contracts';

// Snowflake-scale id: the dataset identity must survive as an opaque string
// through the whole Dataset → Evaluate transition.
const DATASET_ID = '9223372036854775807'; // > Number.MAX_SAFE_INTEGER

const {
  useCaseListMock,
  useDatasetListMock,
  useCreateCasesMock,
  useDeleteCaseMock,
  useAgentListMock,
  useCreateRunConfigMock,
  useTriggerRunMock,
  useToastMock,
} = vi.hoisted(() => ({
  useCaseListMock: vi.fn(),
  useDatasetListMock: vi.fn(),
  useCreateCasesMock: vi.fn(),
  useDeleteCaseMock: vi.fn(),
  useAgentListMock: vi.fn(),
  useCreateRunConfigMock: vi.fn(),
  useTriggerRunMock: vi.fn(),
  useToastMock: vi.fn(),
}));

// vi.mock paths resolve relative to THIS test file (resources/datasets/).
vi.mock('./hooks', () => ({
  useCaseList: useCaseListMock,
  useCreateCases: useCreateCasesMock,
  useDeleteCase: useDeleteCaseMock,
  useDatasetList: useDatasetListMock,
}));

vi.mock('../configs/hooks', () => ({
  useCreateRunConfig: useCreateRunConfigMock,
  useTriggerRun: useTriggerRunMock,
}));

vi.mock('@/modules/agent-management/resources/agents/hooks', () => ({
  useAgentList: useAgentListMock,
}));

vi.mock('@/shared/ui/Toast', () => ({
  useToast: useToastMock,
}));

const dataset: DatasetData = {
  id: DATASET_ID,
  name: 'Regression Set',
  description: null,
  tags: [],
  caseCount: 3,
  isActive: true,
  createdAtUtc: '2026-09-09T00:00:00Z',
  updatedAtUtc: '2026-09-09T00:00:00Z',
};

function renderPage(search = '') {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={[`/evaluation/dataset/${DATASET_ID}${search}`]}>
      <Routes>
        <Route path="/evaluation/dataset/:datasetId" element={<DatasetDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

function datasetSelect() {
  const dialog = screen.getByRole('dialog');
  const select = within(dialog).getAllByRole('combobox')[0] as HTMLSelectElement;
  return select;
}

// FormModal mounts its children one effect after `open`, and the modal seeds
// its draft from initialDatasetId in its own effect — wait for the value to
// settle instead of asserting the intermediate render.
const settledSelect = () => waitFor(() => expect(datasetSelect().value).toBe(DATASET_ID));

describe('DatasetDetailPage evaluate continuity', () => {
  beforeEach(() => {
    useToastMock.mockReturnValue({ toast: vi.fn() });
    useCaseListMock.mockReturnValue({ data: [], isLoading: false });
    useDatasetListMock.mockReturnValue({ data: { items: [dataset], total: 1 } });
    useCreateCasesMock.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
    useDeleteCaseMock.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
    useAgentListMock.mockReturnValue({ data: { items: [{ agentKey: 'agent.docs', displayName: 'Docs Agent' }] } });
    useCreateRunConfigMock.mockReturnValue({ mutateAsync: vi.fn(), isPending: false, error: null, reset: vi.fn() });
    useTriggerRunMock.mockReturnValue({ mutateAsync: vi.fn(), isPending: false, error: null, reset: vi.fn() });
  });

  it('JC-02: the evaluate deep link opens the modal with this dataset preselected', async () => {
    renderPage('?evaluate=1');

    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveTextContent('评估数据集');
    // Deep link + refresh reopen the same modal; the dataset comes from the
    // route param, never from ephemeral state.
    await settledSelect();
    // Never guesses the agent: the target selection stays with the user.
    expect((within(dialog).getAllByRole('combobox')[1] as HTMLSelectElement).value).toBe('');
  });

  it('JC-02: Evaluate Dataset preselects the opened dataset without a deep link', async () => {
    renderPage();

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '评估数据集' }));

    await screen.findByRole('dialog');
    await settledSelect();
  });
});
