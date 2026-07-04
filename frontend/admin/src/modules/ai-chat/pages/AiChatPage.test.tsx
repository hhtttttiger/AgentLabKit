import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { switchTestLanguage } from '@/shared/test/setup';
import { createStorageMock } from '@/shared/test/storage';
import { AiChatPage } from './AiChatPage';
import type { ModelOption, StreamCallbacks } from '../lib/contracts';

const apiMocks = vi.hoisted(() => ({
  streamCardChatMessage: vi.fn(),
  streamAgentChatMessage: vi.fn(),
}));

vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api');
  return {
    ...actual,
    streamCardChatMessage: apiMocks.streamCardChatMessage,
    streamAgentChatMessage: apiMocks.streamAgentChatMessage,
  };
});

vi.mock('@/shared/agent-trace/AgentTraceView', () => ({
  AgentTraceView: () => <div data-testid="agent-trace-view" />,
}));

const storage = createStorageMock();

describe('AiChatPage', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', storage);
    storage.clear();
  });

  afterEach(() => {
    localStorage.clear();
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('creates a session on first send when no session is selected', async () => {
    const user = userEvent.setup();
    await switchTestLanguage('en-US');
    const modelOptions: ModelOption[] = [
      {
        id: 'card.primary',
        name: 'Primary Card',
        type: 'model',
      },
    ];

    apiMocks.streamCardChatMessage.mockImplementation((_modelId: string, _request: unknown, callbacks: StreamCallbacks) => {
      callbacks.onChunk({ content: 'Acknowledged', done: false });
      callbacks.onComplete();
      return vi.fn();
    });

    render(<AiChatPage agentOptions={[]} modelOptions={modelOptions} />);

    expect(screen.getByText('No conversations yet')).toBeInTheDocument();

    await user.type(
      screen.getByPlaceholderText('What would you like to talk about? Type here, press Enter to send, Shift+Enter for a new line'),
      '  Auto title test  {enter}',
    );

    await waitFor(() => {
      expect(screen.getAllByText('Auto title test').length).toBeGreaterThan(0);
    });
    expect(screen.getAllByText('Acknowledged').length).toBeGreaterThan(0);
    expect(apiMocks.streamCardChatMessage).toHaveBeenCalledTimes(1);
  });
});
