import { useState, type ReactNode } from 'react';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '@/shared/test/render';
import type { ToolBindingWriteModel } from '../../lib/contracts';
import type { SkillFlowDocument } from './workbench/lib/types';
import { SkillWorkbenchPage } from './SkillWorkbenchPage';

type MockSkillRecord = {
  id: string;
  skillKey: string;
  displayName: string;
  description: string;
  version: string;
  status: 'draft' | 'published';
  tags: string[];
  promptSections: unknown[];
  toolBindings: ToolBindingWriteModel[];
  configSchema: Record<string, unknown>;
  spec: Record<string, unknown>;
  orchestration: SkillFlowDocument | null;
  createdAtUtc: string;
  updatedAtUtc: string | null;
};

type MockSkillQueryResult = {
  data: MockSkillRecord | undefined;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
};

const baseToolBindings: ToolBindingWriteModel[] = [];

function createSkillQueryResult(overrides: Partial<MockSkillRecord> = {}): MockSkillQueryResult {
  return {
    data: {
      id: 'skill-1',
      skillKey: 'summarize-doc',
      displayName: '文档总结',
      description: 'published skill',
      version: '1.0.0',
      status: 'draft',
      tags: ['nlp'],
      promptSections: [],
      toolBindings: baseToolBindings,
      configSchema: {},
      spec: { custom: { owner: 'ops' } },
      orchestration: null,
      createdAtUtc: '2026-04-08T00:00:00Z',
      updatedAtUtc: null,
      ...overrides,
    },
    isLoading: false,
    isError: false,
    error: null,
  };
}

const {
  applyLayoutMock,
  builderState,
  loadMock,
  mutateAsyncMock,
  resetMock,
  setSelectionMock,
  useSkillMock,
  useSkillMutationsMock,
} = vi.hoisted(() => ({
  applyLayoutMock: vi.fn(),
  builderState: {
    document: {
      version: '3' as const,
      entryStateId: 'start',
      metadata: {
        skillKey: 'summarize-doc',
        displayName: '文档总结',
        description: 'published skill',
        version: '1.0.0',
      },
      states: {
        start: { id: 'start', kind: 'start' as const, title: 'Start' },
        analyze: {
          id: 'analyze',
          kind: 'task' as const,
          title: '分析请求',
          goal: '识别总结目标',
          toolPlan: [],
          inputContract: { inherited: [], required: [], optional: [] },
          outputContract: [],
          fallbackPolicy: { mode: 'stay' as const, note: 'Continue' },
        },
        done: {
          id: 'done',
          kind: 'terminal' as const,
          title: '完成',
          outcome: 'resolved' as const,
          resolutionNote: 'done',
        },
      },
      transitions: {
        'start-analyze': {
          id: 'start-analyze',
          fromStateId: 'start',
          toStateId: 'analyze',
          label: 'Start',
          kind: 'default' as const,
          priority: 0,
        },
        'analyze-done': {
          id: 'analyze-done',
          fromStateId: 'analyze',
          toStateId: 'done',
          label: '完成',
          kind: 'default' as const,
          priority: 0,
        },
      },
    },
    compiled: {
      validation: { isValid: true, errors: [], warnings: [] },
    },
    nodes: [],
    edges: [],
    selection: { kind: 'state' as const, id: 'analyze' },
    dirty: true,
    error: null as string | null,
  },
  loadMock: vi.fn(),
  mutateAsyncMock: vi.fn(),
  resetMock: vi.fn(),
  setSelectionMock: vi.fn(),
  useSkillMock: vi.fn(),
  useSkillMutationsMock: vi.fn(),
}));

vi.mock('./hooks', () => ({
  useSkill: useSkillMock,
  useSkillMutations: useSkillMutationsMock,
}));

vi.mock('./workbench/state/useSkillFlowBuilderStore', () => ({
  SkillFlowBuilderStoreProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  useSkillFlowBuilderState: () => builderState,
  useSkillFlowBuilderActions: () => ({
    load: loadMock,
    reset: resetMock,
    setSelection: setSelectionMock,
    onNodesChange: vi.fn(),
    onEdgesChange: vi.fn(),
    addTaskStateBeforeState: vi.fn(),
    addTaskStateAfterState: vi.fn(),
    addDecisionAfterState: vi.fn(),
    addBranchToDecisionState: vi.fn(),
    updateTaskState: vi.fn(),
    updateDecisionState: vi.fn(),
    updateHandoffState: vi.fn(),
    updateTerminalState: vi.fn(),
    updateTransition: vi.fn(),
    addTaskBranch: vi.fn(),
    deleteState: vi.fn(),
    addToolToTaskState: vi.fn(),
    removeToolFromTaskState: vi.fn(),
    updateToolPlanReason: vi.fn(),
    applyLayout: applyLayoutMock,
  }),
}));

vi.mock('./workbench/components/SkillFlowOutline', () => ({
  SkillFlowOutline: () => <div>步骤目录</div>,
}));

vi.mock('./workbench/components/SkillFlowCanvas', () => ({
  SkillFlowCanvas: () => <div>流程画布</div>,
}));

vi.mock('./workbench/components/SkillFlowInspector', () => ({
  SkillFlowInspector: () => <div>节点检查器</div>,
}));

vi.mock('./workbench/components/SkillFlowValidationPanel', () => ({
  SkillFlowValidationPanel: () => <div>校验结果</div>,
}));

function TestHarness() {
  const [refreshToken, setRefreshToken] = useState(0);

  return (
    <MemoryRouter initialEntries={['/agent-management/skills/summarize-doc/workbench']}>
      <div data-testid="refresh-token" data-token={refreshToken} />
      <button type="button" onClick={() => setRefreshToken((current) => current + 1)}>
        force refresh
      </button>
      <Routes>
        <Route path="/agent-management/skills/:skillKey/workbench" element={<SkillWorkbenchPage />} />
      </Routes>
    </MemoryRouter>
  );
}

function renderPage() {
  return renderWithQueryClient(<TestHarness />);
}

describe('SkillWorkbenchPage', () => {
  beforeEach(() => {
    builderState.dirty = true;
    builderState.error = null;
    loadMock.mockReset();
    mutateAsyncMock.mockReset();
    resetMock.mockReset();
    applyLayoutMock.mockReset();
    setSelectionMock.mockReset();
    useSkillMock.mockReset();

    useSkillMutationsMock.mockReturnValue({
      update: {
        isPending: false,
        error: null,
        reset: vi.fn(),
        mutateAsync: mutateAsyncMock,
      },
      getMutationMessage: vi.fn((error: unknown) => String(error)),
    });
  });

  it('shows a localized loading state while the skill definition is loading', () => {
    useSkillMock.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    });

    renderPage();

    expect(screen.getByText(/正在加载技能编排工作台/)).toBeInTheDocument();
  });

  it('shows a localized error state when the skill cannot be loaded', () => {
    useSkillMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error('missing'),
    });

    renderPage();

    expect(screen.getByText(/missing/)).toBeInTheDocument();
  });

  it('does not break hook ordering when transitioning from loading to loaded', async () => {
    const user = userEvent.setup();
    let currentResult: MockSkillQueryResult = {
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    };
    useSkillMock.mockImplementation(() => currentResult);

    renderPage();

    expect(screen.getByText(/加载技能编排工作台/)).toBeInTheDocument();

    currentResult = createSkillQueryResult();
    await user.click(screen.getByRole('button', { name: 'force refresh' }));

    expect(await screen.findByTestId('skill-workbench-outline-panel')).toBeInTheDocument();
  });

  it('keeps the local draft on refetch and lets the user apply the latest remote version explicitly', async () => {
    const user = userEvent.setup();
    let currentResult: MockSkillQueryResult = createSkillQueryResult();
    useSkillMock.mockImplementation(() => currentResult);

    renderPage();
    await screen.findByTestId('skill-workbench-outline-panel');
    const loadCallsAfterInitialHydrate = loadMock.mock.calls.length;

    currentResult = createSkillQueryResult({
      displayName: 'remote version',
      version: '1.0.1',
      updatedAtUtc: '2026-04-09T00:00:00Z',
    });

    await user.click(screen.getByRole('button', { name: 'force refresh' }));

    expect(await screen.findByTestId('skill-workbench-remote-update')).toBeInTheDocument();
    expect(loadMock.mock.calls.length).toBe(loadCallsAfterInitialHydrate);
    expect(screen.getByText('1.0.0')).toBeInTheDocument();
    expect(screen.getByText('1.0.0')).toBeInTheDocument();

    await user.click(screen.getByTestId('skill-workbench-apply-remote'));

    expect(loadMock.mock.calls.length).toBeGreaterThan(loadCallsAfterInitialHydrate);
    expect(screen.queryByTestId('skill-workbench-remote-update')).not.toBeInTheDocument();
    expect(screen.getByText('1.0.1')).toBeInTheDocument();
  });

  it('saves against the loaded local baseline before the remote version is applied', async () => {
    const user = userEvent.setup();
    let currentResult: MockSkillQueryResult = createSkillQueryResult();
    useSkillMock.mockImplementation(() => currentResult);

    renderPage();
    await screen.findByTestId('skill-workbench-outline-panel');

    currentResult = createSkillQueryResult({
      displayName: 'remote version',
      version: '1.0.1',
      updatedAtUtc: '2026-04-09T00:00:00Z',
      toolBindings: [{
        toolName: 'remote-tool',
        displayName: null,
        description: null,
        invocationMode: 'auto',
        isRequired: false,
        config: {},
        sortOrder: 0,
        isEnabled: true,
      }],
    });

    await user.click(screen.getByRole('button', { name: 'force refresh' }));

    await screen.findByTestId('skill-workbench-remote-update');
    await user.click(screen.getByRole('button', { name: '保存编排' }));

    expect(mutateAsyncMock).toHaveBeenCalledWith(expect.objectContaining({
      model: expect.objectContaining({
        version: '1.0.0',
        spec: expect.objectContaining({
          toolBindings: [],
        }),
      }),
    }));
  });

  it('saves the current orchestration through the existing skill update API', async () => {
    const user = userEvent.setup();

    useSkillMock.mockReturnValue(createSkillQueryResult());

    renderPage();

    expect(screen.getByTestId('skill-workbench-back')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '自动布局' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '保存编排' }));

    expect(loadMock).toHaveBeenCalled();
    expect(mutateAsyncMock).toHaveBeenCalledWith({
      skillKey: 'summarize-doc',
      model: expect.objectContaining({
        spec: expect.objectContaining({
          custom: { owner: 'ops' },
          orchestration: expect.objectContaining({
            entryStateId: 'start',
          }),
        }),
      }),
    });
  });

  it('hides the flow map and validation panels by default', async () => {
    useSkillMock.mockReturnValue(createSkillQueryResult());

    renderPage();

    await screen.findByTestId('skill-workbench-outline-panel');

    expect(screen.getByTestId('skill-workbench-outline-panel')).toBeInTheDocument();
    expect(screen.getByTestId('skill-workbench-inspector-panel')).toBeInTheDocument();
    expect(screen.queryByTestId('skill-workbench-canvas-panel')).not.toBeInTheDocument();
    expect(screen.queryByTestId('skill-workbench-validation-panel')).not.toBeInTheDocument();
    expect(screen.getByTestId('skill-workbench-toggle-flow')).toBeInTheDocument();
    expect(screen.getByTestId('skill-workbench-toggle-validation')).toBeInTheDocument();
  });

  it('shows the flow map and validation panels when toggled on', async () => {
    const user = userEvent.setup();

    useSkillMock.mockReturnValue(createSkillQueryResult());

    renderPage();

    await screen.findByTestId('skill-workbench-outline-panel');

    await user.click(screen.getByTestId('skill-workbench-toggle-flow'));
    await user.click(screen.getByTestId('skill-workbench-toggle-validation'));

    expect(screen.getByTestId('skill-workbench-canvas-panel')).toBeInTheDocument();
    expect(screen.getByTestId('skill-workbench-validation-panel')).toBeInTheDocument();
    expect(screen.getByTestId('skill-workbench-toggle-flow')).toHaveTextContent(/hide/i);
    expect(screen.getByTestId('skill-workbench-toggle-validation')).toHaveTextContent(/hide/i);
  });
});
