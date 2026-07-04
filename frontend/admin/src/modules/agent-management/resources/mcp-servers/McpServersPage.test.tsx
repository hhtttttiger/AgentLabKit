import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '@/shared/test/render';
import { McpServersPage } from './McpServersPage';

const {
  drawerPropsRef,
  useMcpServerListMock,
  useMcpServerMock,
  useMcpServerMutationsMock,
} = vi.hoisted(() => ({
  drawerPropsRef: { current: null as null | Record<string, unknown> },
  useMcpServerListMock: vi.fn(),
  useMcpServerMock: vi.fn(),
  useMcpServerMutationsMock: vi.fn(),
}));

vi.mock('./hooks', () => ({
  useMcpServerList: useMcpServerListMock,
  useMcpServer: useMcpServerMock,
  useMcpServerMutations: useMcpServerMutationsMock,
}));

vi.mock('./McpServerDrawer', () => ({
  McpServerDrawer: (props: Record<string, unknown>) => {
    drawerPropsRef.current = props;

    if (!props.open) {
      return null;
    }

    return (
      <div data-testid="mcp-server-drawer">
        {JSON.stringify(props.initialValue)}
      </div>
    );
  },
}));

describe('McpServersPage', () => {
  beforeEach(() => {
    drawerPropsRef.current = null;

    useMcpServerListMock.mockReturnValue({
      data: [
        {
          id: 'mcp-1',
          name: 'workspace',
          transport: 'http',
          endpoint: 'http://localhost:9000/mcp',
          command: null,
          toolNamePrefix: 'fs_',
          tags: ['prod'],
          isEnabled: true,
          config: { url: 'http://localhost:9000/mcp', toolNamePrefix: 'fs_', tags: ['prod'] },
          createdAtUtc: '2026-04-08T00:00:00Z',
          updatedAtUtc: null,
        },
      ],
      isLoading: false,
      isError: false,
      error: null,
    });

    useMcpServerMock.mockImplementation((name: string) => ({
      data:
        name === 'workspace'
          ? {
              id: 'mcp-1',
              name: 'workspace',
              transport: 'http',
              endpoint: 'http://localhost:9000/mcp',
              command: null,
              toolNamePrefix: 'fs_',
              isEnabled: true,
              tags: ['prod'],
              config: { url: 'http://localhost:9000/mcp', apiKey: 'secret', toolNamePrefix: 'fs_', tags: ['prod'] },
              createdAtUtc: '2026-04-08T00:00:00Z',
              updatedAtUtc: null,
            }
          : undefined,
      isLoading: false,
      isError: false,
      error: null,
    }));

    useMcpServerMutationsMock.mockReturnValue({
      create: {
        isPending: false,
        error: null,
        reset: vi.fn(),
        mutateAsync: vi.fn(),
      },
      update: {
        isPending: false,
        error: null,
        reset: vi.fn(),
        mutateAsync: vi.fn(),
      },
      delete: {
        isPending: false,
        isError: false,
        error: null,
        reset: vi.fn(),
        mutate: vi.fn(),
        mutateAsync: vi.fn(),
      },
      getMutationMessage: vi.fn((error: unknown) => String(error)),
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('loads detail data before opening the edit drawer so config is preserved', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(<McpServersPage />);

    await user.click(screen.getByRole('button', { name: '更多操作' }));
    await user.click(screen.getByRole('menuitem', { name: '编辑' }));

    expect(useMcpServerMock).toHaveBeenLastCalledWith('workspace');
    expect(screen.getByTestId('mcp-server-drawer')).toHaveTextContent('"config":{"url":"http://localhost:9000/mcp","apiKey":"secret","toolNamePrefix":"fs_","tags":["prod"]}');
    expect(drawerPropsRef.current?.mode).toBe('edit');
  });

  it('uses the shared confirm dialog for delete instead of browser confirm', async () => {
    const user = userEvent.setup();
    const mutateAsync = vi.fn().mockResolvedValue(undefined);

    useMcpServerMutationsMock.mockReturnValue({
      create: {
        isPending: false,
        error: null,
        reset: vi.fn(),
        mutateAsync: vi.fn(),
      },
      update: {
        isPending: false,
        error: null,
        reset: vi.fn(),
        mutateAsync: vi.fn(),
      },
      delete: {
        isPending: false,
        isError: false,
        error: null,
        reset: vi.fn(),
        mutate: vi.fn(),
        mutateAsync,
      },
      getMutationMessage: vi.fn((error: unknown) => String(error)),
    });

    renderWithQueryClient(<McpServersPage />);

    await user.click(screen.getByRole('button', { name: '更多操作' }));
    await user.click(screen.getByRole('menuitem', { name: '删除' }));

    expect(screen.getByText('删除 MCP Server')).toBeInTheDocument();
    expect(screen.getByText('确认删除 MCP Server「workspace」吗？')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '确认删除' }));

    expect(mutateAsync).toHaveBeenCalledWith('workspace');
  });
});
