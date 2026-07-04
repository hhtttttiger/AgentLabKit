import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '@/shared/test/render';
import { SkillsPage } from './SkillsPage';

const {
  drawerPropsRef,
  navigateMock,
  removeMutateAsyncMock,
  useSkillListMock,
  useSkillMutationsMock,
} = vi.hoisted(() => ({
  drawerPropsRef: { current: null as null | Record<string, unknown> },
  navigateMock: vi.fn(),
  removeMutateAsyncMock: vi.fn(),
  useSkillListMock: vi.fn(),
  useSkillMutationsMock: vi.fn(),
}));

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock('./hooks', () => ({
  useSkillList: useSkillListMock,
  useSkillMutations: useSkillMutationsMock,
}));

vi.mock('./SkillDrawer', () => ({
  SkillDrawer: (props: Record<string, unknown>) => {
    drawerPropsRef.current = props;
    return props.open ? <div data-testid="skill-drawer" /> : null;
  },
}));

describe('SkillsPage', () => {
  beforeEach(() => {
    drawerPropsRef.current = null;
    navigateMock.mockReset();
    removeMutateAsyncMock.mockReset();

    useSkillListMock.mockReturnValue({
      data: [
        {
          id: 'skill-1',
          skillKey: 'summarize-doc',
          displayName: 'Summarize',
          description: 'Published skill',
          version: '1.0.0',
          status: 'published',
          tags: ['nlp'],
          promptSections: [],
          toolBindings: [],
          configSchema: {},
          spec: {},
          orchestration: null,
          createdAtUtc: '2026-04-08T00:00:00Z',
          updatedAtUtc: null,
        },
      ],
      isLoading: false,
      isError: false,
      error: null,
      isFetching: false,
      refetch: vi.fn(),
    });

    useSkillMutationsMock.mockReturnValue({
      create: { isPending: false, error: null, reset: vi.fn(), mutateAsync: vi.fn() },
      update: { isPending: false, error: null, reset: vi.fn(), mutateAsync: vi.fn() },
      publish: { isPending: false, error: null, mutate: vi.fn() },
      remove: { isPending: false, error: null, reset: vi.fn(), mutateAsync: removeMutateAsyncMock },
      getMutationMessage: vi.fn((error: unknown) => String(error)),
    });
  });

  it('shows edit, orchestration workbench, and delete actions for published skills', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(
      <MemoryRouter>
        <SkillsPage />
      </MemoryRouter>,
    );

    const menuButton = screen.getByRole('button', { name: '更多操作' });
    await user.click(menuButton);

    expect(screen.getByRole('menuitem', { name: '编辑' })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: '编排工作台' })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: '删除' })).toBeInTheDocument();
    expect(screen.queryByRole('menuitem', { name: '发布' })).not.toBeInTheDocument();

    await user.click(screen.getByRole('menuitem', { name: '编辑' }));
    expect(drawerPropsRef.current?.mode).toBe('edit');

    await user.click(menuButton);
    await user.click(screen.getByRole('menuitem', { name: '编排工作台' }));
    expect(navigateMock).toHaveBeenCalledWith('/agent-management/skills/summarize-doc/workbench');

    await user.click(menuButton);
    await user.click(screen.getByRole('menuitem', { name: '删除' }));
    expect(screen.getByText('删除技能')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '确认删除' }));
    expect(removeMutateAsyncMock).toHaveBeenCalledWith('summarize-doc');
  });
});
