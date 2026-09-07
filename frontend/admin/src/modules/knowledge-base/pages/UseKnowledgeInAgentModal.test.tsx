import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { AgentSummaryView, AgentVersionSummaryView, VersionDetailView } from '@/modules/agent-management/lib/contracts';
import { switchTestLanguage } from '@/shared/test/setup';
import { UseKnowledgeInAgentModal } from './UseKnowledgeInAgentModal';

const {
  createVersionMock,
  getVersionDetailMock,
  listVersionsMock,
  updateVersionMock,
  navigateMock,
  toastMock,
} = vi.hoisted(() => ({
  createVersionMock: vi.fn(),
  getVersionDetailMock: vi.fn(),
  listVersionsMock: vi.fn(),
  updateVersionMock: vi.fn(),
  navigateMock: vi.fn(),
  toastMock: vi.fn(),
}));

vi.mock('@/modules/agent-management/resources/agents/hooks', () => ({
  useAgentList: () => ({
    data: {
      items: [{
        agentKey: 'support-agent',
        displayName: 'Support Agent',
        description: null,
        status: 'published',
        publishedVersionNumber: 4,
        rowVersion: 1,
        createdAtUtc: '2026-04-08T00:00:00Z',
        updatedAtUtc: null,
      } satisfies AgentSummaryView],
    },
    isLoading: false,
  }),
}));

vi.mock('@/modules/agent-management/resources/versions/api', () => ({
  createVersion: createVersionMock,
  getVersionDetail: getVersionDetailMock,
  listVersions: listVersionsMock,
  updateVersion: updateVersionMock,
}));

vi.mock('@/shared/ui/Toast', () => ({ useToast: () => ({ toast: toastMock }) }));
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => navigateMock };
});

const versionDetail = (status: 'draft' | 'published', versionNumber: number): VersionDetailView => ({
  versionNumber,
  versionStatus: status,
  versionLabel: `v${versionNumber}`,
  changeSummary: 'existing setup',
  modelKey: 'model.primary',
  checksum: null,
  rowVersion: 9,
  publishedAtUtc: status === 'published' ? '2026-04-08T00:00:00Z' : null,
  createdAtUtc: '2026-04-08T00:00:00Z',
  systemPromptTemplate: 'Preserve this system prompt.',
  defaultLocale: 'en-US',
  runtimeOptions: { timeoutSeconds: 30 },
  handoffPolicy: { mode: 'handoff' },
  responsePolicy: { mode: 'default' },
  guardrailsPolicy: { pii: 'mask' },
  toolBindings: [{
    toolName: 'existing_tool', displayName: 'Existing Tool', description: 'Keep me',
    invocationMode: 'manual_only', isRequired: true, config: { key: 'value' }, sortOrder: 0, isEnabled: true,
  }],
  knowledgeBaseBindings: [{ id: 'existing-kb-binding', knowledgeBaseId: 'old-kb', sortOrder: 0, isEnabled: true, config: { scope: 'all' } }],
  mcpBindings: [{ id: 'mcp-1', serverName: 'workspace', toolWhitelist: ['read_file'], isEnabled: true, configOverrides: {} }],
  skillBindings: [{
    id: 'skill-1', skillKey: 'summarize', displayName: 'Summarize', sortOrder: 0, isEnabled: true,
    configOverrides: { style: 'short' }, toolOverrides: [],
  }],
});

const summary = (status: 'draft' | 'published', versionNumber: number): AgentVersionSummaryView => ({
  versionNumber,
  versionStatus: status,
  versionLabel: `v${versionNumber}`,
  changeSummary: 'existing setup',
  modelKey: 'model.primary',
  checksum: null,
  rowVersion: 9,
  publishedAtUtc: status === 'published' ? '2026-04-08T00:00:00Z' : null,
  createdAtUtc: '2026-04-08T00:00:00Z',
});

function renderModal() {
  return render(
    <UseKnowledgeInAgentModal
      open
      knowledgeBaseId="target-kb"
      knowledgeBaseName="Target KB"
      onClose={vi.fn()}
    />,
  );
}

async function submit() {
  const user = userEvent.setup();
  await user.selectOptions(screen.getByLabelText('Agent'), 'support-agent');
  await user.click(screen.getByRole('button', { name: 'Add knowledge' }));
}

describe('UseKnowledgeInAgentModal lifecycle', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('updates an existing draft and navigates to that draft', async () => {
    await switchTestLanguage('en-US');
    listVersionsMock.mockResolvedValue({ items: [summary('draft', 5), summary('published', 4)], totalCount: 2 });
    getVersionDetailMock.mockResolvedValue(versionDetail('draft', 5));
    updateVersionMock.mockResolvedValue(undefined);

    renderModal();
    await submit();

    await waitFor(() => expect(updateVersionMock).toHaveBeenCalledTimes(1));
    expect(createVersionMock).not.toHaveBeenCalled();
    expect(updateVersionMock).toHaveBeenCalledWith('support-agent', 5, expect.objectContaining({ rowVersion: 9 }));
    const payload = updateVersionMock.mock.calls[0][2];
    expect(payload.systemPromptTemplate).toBe('Preserve this system prompt.');
    expect(payload.toolBindings).toEqual(expect.arrayContaining([
      expect.objectContaining({ toolName: 'existing_tool', config: { key: 'value' } }),
      expect.objectContaining({ toolName: 'knowledge_search', isEnabled: true }),
    ]));
    expect(payload.knowledgeBaseBindings).toEqual(expect.arrayContaining([
      expect.objectContaining({ knowledgeBaseId: 'old-kb' }),
      expect.objectContaining({ knowledgeBaseId: 'target-kb', isEnabled: true }),
    ]));
    expect(navigateMock).toHaveBeenCalledWith(expect.stringContaining('/agents/support-agent?tab=build&version=5'));
  });

  it('seeds a new draft from the published version without mutating Published', async () => {
    await switchTestLanguage('en-US');
    listVersionsMock.mockResolvedValue({ items: [summary('published', 4)], totalCount: 1 });
    getVersionDetailMock.mockResolvedValue(versionDetail('published', 4));
    createVersionMock.mockResolvedValue({ versionNumber: 5 });

    renderModal();
    await submit();

    await waitFor(() => expect(createVersionMock).toHaveBeenCalledTimes(1));
    expect(updateVersionMock).not.toHaveBeenCalled();
    const payload = createVersionMock.mock.calls[0][1];
    expect(payload.systemPromptTemplate).toBe('Preserve this system prompt.');
    expect(payload.modelKey).toBe('model.primary');
    expect(payload.toolBindings).toEqual(expect.arrayContaining([
      expect.objectContaining({ toolName: 'existing_tool', config: { key: 'value' } }),
      expect.objectContaining({ toolName: 'knowledge_search', isEnabled: true }),
    ]));
    expect(payload.knowledgeBaseBindings).toEqual(expect.arrayContaining([
      expect.objectContaining({ knowledgeBaseId: 'old-kb' }),
      expect.objectContaining({ knowledgeBaseId: 'target-kb', isEnabled: true }),
    ]));
    expect(navigateMock).toHaveBeenCalledWith(expect.stringContaining('/agents/support-agent?tab=build&version=5'));
  });
});
