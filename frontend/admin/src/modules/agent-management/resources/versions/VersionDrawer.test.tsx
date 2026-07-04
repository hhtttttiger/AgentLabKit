import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '@/shared/test/render';
import type { VersionDetailView } from '../../lib/contracts';
import { VersionDrawer } from './VersionDrawer';
import type { McpBindingApiView } from '../mcp-servers/types';
import type { VersionKnowledgeBaseBindingApiView } from '../knowledge-base-bindings/types';
import type { SkillBindingApiView } from '../skills/types';

const {
  createVersionToolBindingMock,
  deleteVersionToolBindingMock,
  updateVersionToolBindingMock,
  createVersionKnowledgeBaseBindingMock,
  deleteVersionKnowledgeBaseBindingMock,
  updateVersionKnowledgeBaseBindingMock,
  createVersionMcpBindingMock,
  deleteVersionMcpBindingMock,
  updateVersionMcpBindingMock,
  createVersionSkillBindingMock,
  deleteVersionSkillBindingMock,
  updateVersionSkillBindingMock,
  useToolDefinitionListMock,
  useVersionToolBindingsMock,
  useVersionKnowledgeBaseBindingsMock,
  useVersionMutationsMock,
  useModelListMock,
  listKnowledgeBasesMock,
  useMcpServerListMock,
  useVersionMcpBindingsMock,
  useSkillListMock,
  useVersionSkillBindingsMock,
} = vi.hoisted(() => ({
  createVersionToolBindingMock: vi.fn(),
  deleteVersionToolBindingMock: vi.fn(),
  updateVersionToolBindingMock: vi.fn(),
  createVersionKnowledgeBaseBindingMock: vi.fn(),
  deleteVersionKnowledgeBaseBindingMock: vi.fn(),
  updateVersionKnowledgeBaseBindingMock: vi.fn(),
  createVersionMcpBindingMock: vi.fn(),
  deleteVersionMcpBindingMock: vi.fn(),
  updateVersionMcpBindingMock: vi.fn(),
  createVersionSkillBindingMock: vi.fn(),
  deleteVersionSkillBindingMock: vi.fn(),
  updateVersionSkillBindingMock: vi.fn(),
  useToolDefinitionListMock: vi.fn(),
  useVersionToolBindingsMock: vi.fn(),
  useVersionKnowledgeBaseBindingsMock: vi.fn(),
  useVersionMutationsMock: vi.fn(),
  useModelListMock: vi.fn(),
  listKnowledgeBasesMock: vi.fn(),
  useMcpServerListMock: vi.fn(),
  useVersionMcpBindingsMock: vi.fn(),
  useSkillListMock: vi.fn(),
  useVersionSkillBindingsMock: vi.fn(),
}));

vi.mock('./hooks', () => ({
  useVersionMutations: useVersionMutationsMock,
}));

vi.mock('@/modules/model-management/resources/model-cards/hooks', () => ({
  useModelList: useModelListMock,
}));

vi.mock('@/modules/knowledge-base/resources/knowledge-base/api', () => ({
  listKnowledgeBases: listKnowledgeBasesMock,
}));

vi.mock('../mcp-servers/hooks', () => ({
  useMcpServerList: useMcpServerListMock,
  useVersionMcpBindings: useVersionMcpBindingsMock,
}));

vi.mock('../knowledge-base-bindings/hooks', () => ({
  useVersionKnowledgeBaseBindings: useVersionKnowledgeBaseBindingsMock,
}));

vi.mock('../knowledge-base-bindings/api', () => ({
  createVersionKnowledgeBaseBinding: createVersionKnowledgeBaseBindingMock,
  deleteVersionKnowledgeBaseBinding: deleteVersionKnowledgeBaseBindingMock,
  updateVersionKnowledgeBaseBinding: updateVersionKnowledgeBaseBindingMock,
}));

vi.mock('../mcp-servers/api', () => ({
  createVersionMcpBinding: createVersionMcpBindingMock,
  deleteVersionMcpBinding: deleteVersionMcpBindingMock,
  updateVersionMcpBinding: updateVersionMcpBindingMock,
}));

vi.mock('../skills/hooks', () => ({
  useSkillList: useSkillListMock,
  useVersionSkillBindings: useVersionSkillBindingsMock,
}));

vi.mock('../skills/api', () => ({
  createVersionSkillBinding: createVersionSkillBindingMock,
  deleteVersionSkillBinding: deleteVersionSkillBindingMock,
  updateVersionSkillBinding: updateVersionSkillBindingMock,
}));

vi.mock('../tools/hooks', () => ({
  createVersionToolBinding: createVersionToolBindingMock,
  deleteVersionToolBinding: deleteVersionToolBindingMock,
  updateVersionToolBinding: updateVersionToolBindingMock,
  useToolDefinitionList: useToolDefinitionListMock,
  useVersionToolBindings: useVersionToolBindingsMock,
}));

const editVersion: VersionDetailView = {
  versionNumber: 2,
  versionStatus: 'draft',
  versionLabel: 'v2',
  changeSummary: 'skills updated',
  modelKey: 'binding.primary',
  checksum: null,
  rowVersion: 3,
  publishedAtUtc: null,
  createdAtUtc: '2026-04-08T00:00:00Z',
  systemPromptTemplate: 'You are helpful.',
  defaultLocale: 'zh-CN',
  runtimeOptions: {},
  handoffPolicy: {},
  responsePolicy: { mode: 'default' },
  guardrailsPolicy: {},
  toolBindings: [{
    toolName: 'knowledge_search',
    displayName: 'Knowledge Search',
    description: null,
    invocationMode: 'auto',
    isRequired: false,
    config: {},
    sortOrder: 0,
    isEnabled: true,
  }],
  knowledgeBaseBindings: [{
    id: 'binding-1',
    knowledgeBaseId: 'kb-1',
    sortOrder: 10,
    isEnabled: true,
    config: {},
  }],
  mcpBindings: [{
    id: 'mcp-1',
    serverName: 'workspace',
    isEnabled: true,
    toolWhitelist: ['read_file'],
    configOverrides: {},
  }],
  skillBindings: [{
    id: '1',
    skillKey: 'summarize-doc',
    displayName: 'Summarize',
    sortOrder: 0,
    isEnabled: true,
    configOverrides: {},
    toolOverrides: [{
      toolName: 'summarize_tool',
      displayName: 'Summarizer',
      description: null,
      invocationMode: 'manual_only',
      isRequired: false,
      config: {},
      sortOrder: 0,
      isEnabled: true,
    }],
  }],
};

describe('VersionDrawer', () => {
  beforeEach(() => {
    createVersionToolBindingMock.mockResolvedValue(undefined);
    deleteVersionToolBindingMock.mockResolvedValue(undefined);
    updateVersionToolBindingMock.mockResolvedValue(undefined);
    createVersionKnowledgeBaseBindingMock.mockResolvedValue(undefined);
    deleteVersionKnowledgeBaseBindingMock.mockResolvedValue(undefined);
    updateVersionKnowledgeBaseBindingMock.mockResolvedValue(undefined);
    createVersionMcpBindingMock.mockResolvedValue(undefined);
    deleteVersionMcpBindingMock.mockResolvedValue(undefined);
    updateVersionMcpBindingMock.mockResolvedValue(undefined);
    createVersionSkillBindingMock.mockResolvedValue(undefined);
    deleteVersionSkillBindingMock.mockResolvedValue(undefined);
    updateVersionSkillBindingMock.mockResolvedValue(undefined);

    useVersionMutationsMock.mockReturnValue({
      create: { isPending: false, error: null, reset: vi.fn(), mutateAsync: vi.fn() },
      update: {
        isPending: false,
        error: null,
        reset: vi.fn(),
        mutateAsync: vi.fn().mockResolvedValue(editVersion),
      },
      getMutationMessage: vi.fn((error: unknown) => String(error)),
    });

    useModelListMock.mockReturnValue({
      data: {
        items: [{
          modelKey: 'binding.primary',
          displayName: 'Primary',
          provider: 'openai',
          model: 'gpt-4.1',
          type: 'chat',
          isEnabled: true,
          createdAtUtc: '2026-04-08T00:00:00Z',
          updatedAtUtc: null,
        }],
      },
      isLoading: false,
    });
    listKnowledgeBasesMock.mockResolvedValue({
      items: [{
        id: 'kb-1',
        name: 'Policies',
        description: 'Policy docs',
        sourceType: 'local',
        documentCount: 12,
        status: 'Active',
        createdAtUtc: '2026-04-08T00:00:00Z',
      }],
      totalCount: 1,
      page: 1,
      pageSize: 100,
    });

    useMcpServerListMock.mockReturnValue({ data: [{ name: 'workspace' }] });
    useToolDefinitionListMock.mockReturnValue({
      data: [{ toolName: 'knowledge_search', displayName: 'Knowledge Search', sourceType: 'builtin' }],
    });
    useVersionToolBindingsMock.mockReturnValue({
      data: [{
        id: 'tool-1',
        toolName: 'knowledge_search',
        displayName: 'Knowledge Search',
        description: null,
        invocationMode: 'auto',
        isRequired: false,
        sortOrder: 0,
        isEnabled: true,
        config: {},
        createdAtUtc: '2026-04-08T00:00:00Z',
        updatedAtUtc: null,
      }],
      isLoading: false,
    });
    useVersionKnowledgeBaseBindingsMock.mockReturnValue({
      data: [{
        id: 'binding-1',
        knowledgeBaseId: 'kb-1',
        sortOrder: 10,
        isEnabled: true,
        config: {},
        createdAtUtc: '2026-04-08T00:00:00Z',
        updatedAtUtc: null,
      } satisfies VersionKnowledgeBaseBindingApiView],
      isLoading: false,
    });
    useVersionMcpBindingsMock.mockReturnValue({
      data: [{
        id: 'mcp-1',
        serverName: 'workspace',
        isEnabled: true,
        toolWhitelist: ['read_file'],
        configOverrides: {},
        createdAtUtc: '2026-04-08T00:00:00Z',
        updatedAtUtc: null,
      }],
      isLoading: false,
    });
    useSkillListMock.mockReturnValue({ data: [{ skillKey: 'summarize-doc', displayName: 'Summarize' }] });
    useVersionSkillBindingsMock.mockReturnValue({
      data: [{
        id: '1',
        skillKey: 'summarize-doc',
        isEnabled: true,
        bindingOrder: 0,
        config: {},
        toolOverrides: [{
          toolName: 'summarize_tool',
          displayName: 'Summarizer',
          description: null,
          invocationMode: 'manual_only',
          isRequired: false,
          config: {},
          sortOrder: 0,
          isEnabled: true,
        }],
        createdAtUtc: '2026-04-08T00:00:00Z',
        updatedAtUtc: null,
      }],
      isLoading: false,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders editable skill tool overrides inside the skill binding section', () => {
    renderWithQueryClient(
      <VersionDrawer
        open
        agentKey="agent.docs"
        editVersion={editVersion}
        onClose={() => {}}
      />,
    );

    expect(screen.getByText('工具覆盖')).toBeInTheDocument();
    expect(screen.getByDisplayValue('summarize_tool')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Summarizer')).toBeInTheDocument();
  });

  it('renders the knowledge base binding section inside the version drawer', async () => {
    renderWithQueryClient(
      <VersionDrawer
        open
        agentKey="agent.docs"
        editVersion={editVersion}
        onClose={() => {}}
      />,
    );

    expect(await screen.findByText('知识库绑定')).toBeInTheDocument();
    expect(await screen.findByText('Policies')).toBeInTheDocument();
  });

  it('renders the knowledge base binding section as read-only for published versions', async () => {
    renderWithQueryClient(
      <VersionDrawer
        open
        agentKey="agent.docs"
        readOnly
        editVersion={{ ...editVersion, versionStatus: 'published', publishedAtUtc: '2026-04-30T00:00:00Z' }}
        onClose={() => {}}
      />,
    );

    expect(await screen.findByText(/知识库绑定不可直接修改/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '新增知识库绑定' })).not.toBeInTheDocument();
  });

  it('labels advanced guardrails policy as agent-local only', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(
      <VersionDrawer
        open
        agentKey="agent.docs"
        editVersion={editVersion}
        onClose={() => {}}
      />,
    );

    await user.click(screen.getByRole('button', { name: /高级策略配置/i }));

    expect(screen.getByText('以下高级 JSON 策略仅作用于当前 agent version；留空时系统将使用默认策略。')).toBeInTheDocument();
    expect(screen.getByLabelText('Agent 本地 Guardrails 策略')).toBeInTheDocument();
    expect(screen.queryByText(/Global Guardrails/i)).not.toBeInTheDocument();
  });

  it('submits aggregate bindings in the version update request', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    renderWithQueryClient(
      <VersionDrawer
        open
        agentKey="agent.docs"
        editVersion={editVersion}
        onClose={onClose}
      />,
    );

    await user.click(screen.getByRole('button', { name: '保存修改' }));

    await waitFor(() => {
      const updateCall = useVersionMutationsMock.mock.results[0]?.value.update.mutateAsync.mock.calls[0]?.[0];

      expect(updateCall).toEqual({
        versionNumber: 2,
        model: {
          systemPromptTemplate: 'You are helpful.',
          modelKey: 'binding.primary',
          versionLabel: 'v2',
          changeSummary: 'skills updated',
          defaultLocale: 'zh-CN',
          runtimeOptions: {},
          handoffPolicy: {},
          responsePolicy: { mode: 'default' },
          guardrailsPolicy: {},
          toolBindings: [{
            toolName: 'knowledge_search',
            displayName: 'Knowledge Search',
            description: null,
            invocationMode: 'auto',
            isRequired: false,
            sortOrder: 0,
            isEnabled: true,
            config: {},
          }],
          knowledgeBaseBindings: [{
            knowledgeBaseId: 'kb-1',
            sortOrder: 10,
            isEnabled: true,
            config: {},
          }],
          mcpBindings: [{
            serverName: 'workspace',
            isEnabled: true,
            toolWhitelist: ['read_file'],
            configOverrides: {},
          }],
          skillBindings: [{
            skillKey: 'summarize-doc',
            isEnabled: true,
            bindingOrder: 0,
            config: {},
            toolOverrides: [{
              toolName: 'summarize_tool',
              displayName: 'Summarizer',
              description: null,
              invocationMode: 'manual_only',
              isRequired: false,
              sortOrder: 0,
              isEnabled: true,
              config: {},
            }],
          }],
          rowVersion: 3,
        },
      });
      expect(createVersionToolBindingMock).not.toHaveBeenCalled();
      expect(updateVersionToolBindingMock).not.toHaveBeenCalled();
      expect(deleteVersionToolBindingMock).not.toHaveBeenCalled();
      expect(createVersionKnowledgeBaseBindingMock).not.toHaveBeenCalled();
      expect(updateVersionKnowledgeBaseBindingMock).not.toHaveBeenCalled();
      expect(deleteVersionKnowledgeBaseBindingMock).not.toHaveBeenCalled();
      expect(createVersionMcpBindingMock).not.toHaveBeenCalled();
      expect(updateVersionMcpBindingMock).not.toHaveBeenCalled();
      expect(deleteVersionMcpBindingMock).not.toHaveBeenCalled();
      expect(createVersionSkillBindingMock).not.toHaveBeenCalled();
      expect(updateVersionSkillBindingMock).not.toHaveBeenCalled();
      expect(deleteVersionSkillBindingMock).not.toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('preserves in-progress draft edits when binding queries finish loading', async () => {
    const user = userEvent.setup();
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    const mcpBindingsState: {
      data: McpBindingApiView[] | undefined;
      isLoading: boolean;
    } = {
      data: undefined,
      isLoading: true,
    };
    const skillBindingsState: {
      data: SkillBindingApiView[] | undefined;
      isLoading: boolean;
    } = {
      data: undefined,
      isLoading: true,
    };

    useVersionMcpBindingsMock.mockImplementation(() => mcpBindingsState);
    useVersionSkillBindingsMock.mockImplementation(() => skillBindingsState);

    const view = render(
      <QueryClientProvider client={queryClient}>
          <VersionDrawer
            open
            agentKey="agent.docs"
            editVersion={editVersion}
            onClose={() => {}}
          />
      </QueryClientProvider>,
    );

    const promptInput = await screen.findByLabelText('System Prompt');
    await user.clear(promptInput);
    await user.type(promptInput, 'Draft prompt in progress');
    expect(screen.getByDisplayValue('Draft prompt in progress')).toBeInTheDocument();

    mcpBindingsState.data = [{
      id: 'mcp-1',
      serverName: 'workspace',
      isEnabled: true,
      toolWhitelist: ['read_file'],
      configOverrides: {},
      createdAtUtc: '2026-04-08T00:00:00Z',
      updatedAtUtc: null,
    }];
    mcpBindingsState.isLoading = false;
    skillBindingsState.data = [{
      id: '1',
      skillKey: 'summarize-doc',
      isEnabled: true,
      bindingOrder: 0,
      config: {},
      toolOverrides: [{
        toolName: 'summarize_tool',
        displayName: 'Summarizer',
        description: null,
        invocationMode: 'manual_only',
        isRequired: false,
        config: {},
        sortOrder: 0,
        isEnabled: true,
      }],
      createdAtUtc: '2026-04-08T00:00:00Z',
      updatedAtUtc: null,
    }];
    skillBindingsState.isLoading = false;

    view.rerender(
      <QueryClientProvider client={queryClient}>
          <VersionDrawer
            open
            agentKey="agent.docs"
            editVersion={editVersion}
            onClose={() => {}}
          />
      </QueryClientProvider>,
    );

    expect(screen.getByDisplayValue('Draft prompt in progress')).toBeInTheDocument();
  });

  it('preserves in-progress draft edits when the same version detail is refreshed', async () => {
    const user = userEvent.setup();
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    const initialVersion = editVersion;
    const refreshedVersion: VersionDetailView = {
      ...editVersion,
      toolBindings: editVersion.toolBindings.map((binding) => ({ ...binding })),
    };

    const view = render(
      <QueryClientProvider client={queryClient}>
          <VersionDrawer
            open
            agentKey="agent.docs"
            editVersion={initialVersion}
            onClose={() => {}}
          />
      </QueryClientProvider>,
    );

    const promptInput = await screen.findByLabelText('System Prompt');
    await user.clear(promptInput);
    await user.type(promptInput, 'Edited prompt should stay');
    expect(screen.getByDisplayValue('Edited prompt should stay')).toBeInTheDocument();

    view.rerender(
      <QueryClientProvider client={queryClient}>
          <VersionDrawer
            open
            agentKey="agent.docs"
            editVersion={refreshedVersion}
            onClose={() => {}}
          />
      </QueryClientProvider>,
    );

    expect(screen.getByDisplayValue('Edited prompt should stay')).toBeInTheDocument();
  });
});
