import { act, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { switchTestLanguage } from '@/shared/test/setup';
import { SessionList } from './SessionList';
import type { ChatSession } from '../lib/contracts';

describe('SessionList relative timestamps', () => {
  function buildSession(updatedAt: number): ChatSession {
    return {
      id: 'session-1',
      title: 'Session title',
      modelType: 'agent',
      modelId: 'agent-1',
      messages: [
        {
          id: 'message-1',
          role: 'assistant',
          content: 'A recent assistant message',
          timestamp: updatedAt,
        },
      ],
      createdAt: updatedAt,
      updatedAt,
    };
  }

  it('rerenders locale-aware recent timestamps when the admin language changes', async () => {
    const now = Date.now();

    await switchTestLanguage('en-US');
    const recentSession = buildSession(now - 3 * 60_000);
    render(
      <SessionList
        sessions={[recentSession]}
        currentSessionId={recentSession.id}
        onSelect={vi.fn()}
        onNewChat={vi.fn()}
      />,
    );

    const enText = new Intl.RelativeTimeFormat('en-US', { numeric: 'auto' }).format(-3, 'minute');
    const zhText = new Intl.RelativeTimeFormat('zh-CN', { numeric: 'auto' }).format(-3, 'minute');

    expect(screen.getByText(enText)).toBeInTheDocument();

    await act(async () => {
      await switchTestLanguage('zh-CN');
    });

    await waitFor(() => {
      expect(screen.getByText(zhText)).toBeInTheDocument();
    });
    expect(screen.queryByText(enText)).not.toBeInTheDocument();
  });

  it('renders session chrome from translations', async () => {
    await switchTestLanguage('en-US');

    const now = Date.now();
    render(
      <SessionList
        sessions={[buildSession(now)]}
        currentSessionId="session-1"
        onSelect={vi.fn()}
        onDelete={vi.fn()}
        onNewChat={vi.fn()}
      />,
    );

    expect(screen.getByText('Sessions')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'New chat' })).toBeInTheDocument();
    expect(screen.getByTitle('Delete conversation')).toBeInTheDocument();
  });
});
