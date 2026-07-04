import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { switchTestLanguage } from '@/shared/test/setup';
import { createStorageMock } from '@/shared/test/storage';
import {
  clearAll,
  createSession as createChatSession,
  deleteSession,
  loadSessions,
  saveSession,
} from './chat-history';
import type { ChatSession } from './contracts';

const storage = createStorageMock();

function createSession(overrides: Partial<ChatSession> = {}): ChatSession {
  return {
    id: overrides.id ?? 'session-1',
    title: overrides.title ?? 'Session',
    modelType: overrides.modelType ?? 'model',
    modelId: overrides.modelId ?? 'card.primary',
    messages: overrides.messages ?? [],
    createdAt: overrides.createdAt ?? 100,
    updatedAt: overrides.updatedAt ?? 100,
  };
}

describe('chat-history', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', storage);
    storage.clear();
  });

  afterEach(() => {
    clearAll();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('loads sessions ordered by most recent update first', () => {
    saveSession(createSession({ id: 'older', updatedAt: 10 }));
    saveSession(createSession({ id: 'newer', updatedAt: 20 }));

    expect(loadSessions().map((session) => session.id)).toEqual(['newer', 'older']);
  });

  it('trims oversized message histories before persisting', () => {
    const session = createSession({
      messages: Array.from({ length: 505 }, (_, index) => ({
        id: `msg-${index}`,
        role: 'user' as const,
        content: `message-${index}`,
        timestamp: index,
      })),
    });

    saveSession(session);

    const [stored] = loadSessions();
    expect(stored.messages).toHaveLength(500);
    expect(stored.messages[0]?.content).toBe('message-5');
    expect(session.messages).toHaveLength(505);
  });

  it('deletes a single session without clearing the rest', () => {
    saveSession(createSession({ id: 'keep' }));
    saveSession(createSession({ id: 'remove', updatedAt: 200 }));

    deleteSession('remove');

    expect(loadSessions().map((session) => session.id)).toEqual(['keep']);
  });

  it('creates default titles with the admin locale time', async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-04-14T08:09:10Z'));

    await switchTestLanguage('en-US');
    expect(createChatSession({ modelType: 'model', modelId: 'card.primary' }).title).toBe(
      `New chat ${new Date().toLocaleTimeString('en-US')}`,
    );

    await switchTestLanguage('zh-CN');
    expect(createChatSession({ modelType: 'model', modelId: 'card.primary' }).title).toBe(
      `新对话 ${new Date().toLocaleTimeString('zh-CN')}`,
    );
  });
});
