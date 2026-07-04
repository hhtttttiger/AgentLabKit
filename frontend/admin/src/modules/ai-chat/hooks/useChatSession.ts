/**
 * AI Chat Module — useChatSession Hook
 * Session CRUD with API-first + localStorage cache fallback.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import type { ChatSession, ModelOption } from '../lib/contracts';
import { dtoToMessage, dtoToSession, isServerSessionId } from '../lib/contracts';
import {
  fetchChatSessions,
  createChatSession as apiCreateSession,
  deleteChatSession as apiDeleteSession,
  fetchChatMessages,
} from '../api';
import {
  loadSessions,
  persistSessionsSnapshot,
  debouncedSaveSession,
  cancelDebouncedSave,
  createSession,
} from '../lib/chat-history';
import { buildSessionTitle } from '../lib/session-title';

export function useChatSession(_selectedModel: ModelOption | null) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const currentSessionRef = useRef<ChatSession | null>(null);

  // ── Init — fetch sessions from API, localStorage fallback ──────────

  useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        const result = await fetchChatSessions(1, 50);
        if (cancelled) return;

        const mapped = result.items.map(dtoToSession);
        setSessions(mapped);
        persistSessionsSnapshot(mapped);

        if (mapped.length > 0) {
          selectSession(mapped[0], { silent: true });
        }
      } catch {
        if (cancelled) return;
        // Offline fallback
        const cached = loadSessions();
        setSessions(cached);
        if (cached.length > 0) {
          selectSession(cached[0], { silent: true });
        }
      } finally {
        if (!cancelled) setIsLoadingSessions(false);
      }
    }

    init();
    return () => {
      cancelled = true;
      cancelDebouncedSave();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Sync ref ───────────────────────────────────────────────────────

  useEffect(() => {
    currentSessionRef.current = currentSession;
  }, [currentSession]);

  // ── Select session (fetch messages from API) ────────────────────────

  const selectSession = useCallback(async (
    session: ChatSession,
    opts?: { silent?: boolean },
  ) => {
    setCurrentSession(session);
    currentSessionRef.current = session;

    if (isServerSessionId(session.id)) {
      try {
        setIsLoadingMessages(true);
        const result = await fetchChatMessages(session.id);
        const messages = result.messages.map(dtoToMessage);
        const populated: ChatSession = { ...session, messages };
        setCurrentSession(populated);
        currentSessionRef.current = populated;
      } catch {
        // Keep session with cached/local messages
      } finally {
        setIsLoadingMessages(false);
      }
    } else if (!opts?.silent) {
      setCurrentSession(session);
      currentSessionRef.current = session;
    }
  }, []);

  // ── Reset current session (no server call — for "New Chat") ────────

  const resetCurrentSession = useCallback(() => {
    setCurrentSession(null);
    currentSessionRef.current = null;
  }, []);

  // ── Create session on-demand (called from sendMessage) ──────────────
  // Creates a server-side session; falls back to local-only on API error.

  const createSessionForMessage = useCallback(async (
    model: ModelOption,
    firstMessage: string,
  ): Promise<ChatSession> => {
    const title = buildSessionTitle(model.name, firstMessage);

    try {
      const dto = await apiCreateSession({
        title,
        modelType: model.type,
        modelId: model.id,
      });
      const session = dtoToSession(dto);
      setSessions((prev) => {
        const next = [session, ...prev];
        persistSessionsSnapshot(next);
        return next;
      });
      setCurrentSession(session);
      currentSessionRef.current = session;
      return session;
    } catch {
      // Fallback to local-only session
      const localSession = createSession({
        modelType: model.type,
        modelId: model.id,
        title,
      });
      setSessions((prev) => [localSession, ...prev]);
      setCurrentSession(localSession);
      currentSessionRef.current = localSession;
      return localSession;
    }
  }, []);

  // ── Delete session ─────────────────────────────────────────────────

  const deleteSession = useCallback(async (sessionId: number | string) => {
    if (isServerSessionId(sessionId)) {
      try {
        await apiDeleteSession(sessionId);
      } catch {
        // Proceed with local removal even if API fails
      }
    }

    setSessions((prev) => {
      const next = prev.filter((s) => s.id !== sessionId);
      if (currentSession?.id === sessionId) {
        const nextSession = next[0] ?? null;
        setCurrentSession(nextSession);
        currentSessionRef.current = nextSession;
      }
      persistSessionsSnapshot(next);
      return next;
    });
  }, [currentSession]);

  // ── Session update (persisted, with debounced cache) ────────────────

  const applySessionUpdate = useCallback((session: ChatSession) => {
    setCurrentSession(session);
    currentSessionRef.current = session;
    setSessions((prev) => {
      const exists = prev.some((s) => s.id === session.id);
      const next = exists
        ? prev.map((s) => (s.id === session.id ? session : s))
        : [session, ...prev];
      const sorted = [...next].sort((a, b) => b.updatedAt - a.updatedAt);
      debouncedSaveSession(session);
      return sorted;
    });
  }, []);

  // ── Transient update (no persistence — for streaming) ──────────────

  const applyTransientSessionUpdate = useCallback((session: ChatSession) => {
    setCurrentSession(session);
    currentSessionRef.current = session;
    setSessions((prev) =>
      prev.map((s) => (s.id === session.id ? session : s)),
    );
  }, []);

  return {
    sessions,
    currentSession,
    isLoadingSessions,
    isLoadingMessages,
    currentSessionRef,
    selectSession,
    resetCurrentSession,
    createSessionForMessage,
    deleteSession,
    applySessionUpdate,
    applyTransientSessionUpdate,
  };
}
