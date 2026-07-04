/**
 * AI Chat Module - Chat History Management
 * Handles localStorage persistence for chat sessions
 */

import { formatAdminTime } from '@/shared/i18n/formatters';
import i18n from '@/shared/i18n';
import type { ChatSession } from './contracts';

const STORAGE_KEY = 'ai-chat-sessions';
const MAX_SESSIONS = 50;
const MAX_MESSAGES_PER_SESSION = 500;

/**
 * Load all sessions from localStorage
 */
export function loadSessions(): ChatSession[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];

    // Migrate legacy 'card' → 'model' (unified terminology)
    const sessions = (JSON.parse(stored) as ChatSession[]).map((session) => ({
      ...session,
      modelType: (session.modelType as string) === 'card' ? 'model' as const : session.modelType,
    }));

    // Sort by updatedAt descending (most recent first)
    return sessions.sort((a, b) => b.updatedAt - a.updatedAt);
  } catch (error) {
    console.error('Failed to load chat sessions:', error);
    return [];
  }
}

/**
 * Save a session to localStorage
 */
export function saveSession(session: ChatSession): void {
  try {
    const sessions = loadSessions();
    const normalizedSession = {
      ...session,
      messages: session.messages.slice(-MAX_MESSAGES_PER_SESSION),
    };

    const existingIndex = sessions.findIndex((s) => s.id === normalizedSession.id);

    if (existingIndex >= 0) {
      sessions[existingIndex] = normalizedSession;
    } else {
      sessions.push(normalizedSession);
    }

    const limitedSessions = sessions
      .sort((a, b) => b.updatedAt - a.updatedAt)
      .slice(0, MAX_SESSIONS);

    localStorage.setItem(STORAGE_KEY, JSON.stringify(limitedSessions));
  } catch (error) {
    console.error('Failed to save chat session:', error);
  }
}

/**
 * Delete a session from localStorage
 */
export function deleteSession(id: string): void {
  try {
    const sessions = loadSessions().filter((s) => s.id !== id);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  } catch (error) {
    console.error('Failed to delete chat session:', error);
  }
}

/**
 * Get a specific session by ID
 */
export function getSession(id: string): ChatSession | undefined {
  const sessions = loadSessions();
  return sessions.find((s) => s.id === id);
}

/**
 * Delete all sessions
 */
export function clearAll(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (error) {
    console.error('Failed to clear chat sessions:', error);
  }
}

/**
 * Generate a unique session ID
 */
export function generateSessionId(): string {
  return `session-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Generate a unique message ID
 */
export function generateMessageId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Create a new session with default values
 */
export function createSession(options: {
  modelType: 'agent' | 'model';
  modelId: string;
  title?: string;
}): ChatSession {
  const now = Date.now();
  const time = formatAdminTime(now);
  return {
    id: generateSessionId(),
    title: options.title ?? i18n.t('modules.aiChat.sessionList.defaultTitle', { time }),
    modelType: options.modelType,
    modelId: options.modelId,
    messages: [],
    createdAt: now,
    updatedAt: now,
  };
}

/**
 * Add a message to a session
 */
export function addMessageToSession(
  session: ChatSession,
  message: Omit<ChatSession['messages'][0], 'id'>
): ChatSession {
  const newMessage = {
    id: generateMessageId(),
    ...message,
  };

  return {
    ...session,
    messages: [...session.messages, newMessage],
    updatedAt: Date.now(),
  };
}

/**
 * Update a message in a session
 */
export function updateMessageInSession(
  session: ChatSession,
  messageId: string,
  updates: Partial<ChatSession['messages'][0]>
): ChatSession {
  return {
    ...session,
    messages: session.messages.map((msg) =>
      msg.id === messageId ? { ...msg, ...updates } : msg
    ),
    updatedAt: Date.now(),
  };
}

// ──────────────────────────────────────────────────────────────────────
// Cache-layer helpers (API is source of truth, localStorage is fallback)
// ──────────────────────────────────────────────────────────────────────

let _debounceTimer: ReturnType<typeof setTimeout> | null = null;

/**
 * Debounced write — coalesces rapid updates (e.g. streaming) into a single
 * localStorage write after 1s of inactivity.
 */
export function debouncedSaveSession(session: ChatSession, delayMs: number = 1000): void {
  if (_debounceTimer !== null) {
    clearTimeout(_debounceTimer);
  }
  _debounceTimer = setTimeout(() => {
    saveSession(session);
    _debounceTimer = null;
  }, delayMs);
}

/**
 * Persist a full session list snapshot — used after API fetch or bulk
 * operations (page load, session delete).
 */
export function persistSessionsSnapshot(sessions: ChatSession[]): void {
  try {
    const serialized = sessions.map((s) => ({
      ...s,
      messages: s.messages.slice(-200), // cap cached messages per session
    }));
    localStorage.setItem(STORAGE_KEY, JSON.stringify(serialized));
  } catch (error) {
    console.error('Failed to persist sessions snapshot:', error);
  }
}

/**
 * Detect localStorage sessions that don't have a server-side counterpart,
 * for one-time migration prompts.
 */
export function detectUnsavedSessions(serverSessionIds: Set<string>): ChatSession[] {
  const local = loadSessions();
  return local.filter((s) => {
    // Server IDs are snowflake numbers serialized as strings (JS precision limit).
    // Local-only IDs look like "session-{ts}-{rand}".
    const id = String(s.id);
    // If the ID looks like a server-assigned snowflake, check membership.
    if (/^\d{16,}$/.test(id)) {
      return !serverSessionIds.has(id);
    }
    // Non-numeric ID → local-only session, always "unsaved".
    return true;
  });
}

/**
 * Cancel any pending debounced save (call on unmount).
 */
export function cancelDebouncedSave(): void {
  if (_debounceTimer !== null) {
    clearTimeout(_debounceTimer);
    _debounceTimer = null;
  }
}
