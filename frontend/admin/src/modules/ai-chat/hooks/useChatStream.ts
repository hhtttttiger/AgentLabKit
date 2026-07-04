/**
 * AI Chat Module — useChatStream Hook
 * Unified sendMessage + streaming with rAF-throttled UI updates.
 *
 * Session creation is deferred: a server-side session is only created
 * when the user actually sends a message (not on page load or mode switch).
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { isServerSessionId } from '../lib/contracts';
import type { ChatMessage, ChatSession, ModelOption } from '../lib/contracts';
import {
  buildHistory,
  mergeAgentTrace,
} from '../lib/agent-trace-merge';
import {
  addMessageToSession,
  generateMessageId,
  updateMessageInSession,
} from '../lib/chat-history';
import {
  streamAgentChatMessage,
  streamCardChatMessage,
  accumulateStreamContent,
  saveChatTurn,
} from '../api';

type SessionRef = React.MutableRefObject<ChatSession | null>;
type ApplyUpdate = (session: ChatSession) => void;
type CreateSessionForMessage = (
  model: ModelOption,
  firstMessage: string,
) => Promise<ChatSession>;

export function useChatStream(
  currentSessionRef: SessionRef,
  applySessionUpdate: ApplyUpdate,
  applyTransientSessionUpdate: ApplyUpdate,
  selectedModelRef: React.MutableRefObject<ModelOption | null>,
  pendingModeSwitchRef: React.MutableRefObject<boolean>,
  createSessionForMessage: CreateSessionForMessage,
) {
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<(() => void) | null>(null);
  // Accumulate assistant content synchronously so onComplete always saves
  // the final text, not stale state from the rAF throttle.
  const assistantContentRef = useRef<string>('');

  // Keep refs accessible in callbacks without re-creating them
  const createSessionRef = useRef(createSessionForMessage);
  useEffect(() => {
    createSessionRef.current = createSessionForMessage;
  }, [createSessionForMessage]);

  // ── rAF throttle ───────────────────────────────────────────────────

  const rafRef = useRef<number | null>(null);
  const pendingUpdateRef = useRef<ApplyUpdate | null>(null);

  const scheduleUpdate = useCallback(
    (updater: ApplyUpdate) => {
      pendingUpdateRef.current = updater;
      if (rafRef.current === null) {
        rafRef.current = requestAnimationFrame(() => {
          const fn = pendingUpdateRef.current;
          pendingUpdateRef.current = null;
          rafRef.current = null;
          const session = currentSessionRef.current;
          if (session && fn) fn(session);
        });
      }
    },
    [currentSessionRef],
  );

  // Synchronously flush any pending rAF update — used in onComplete so
  // saveChatTurn sees the final assistant content, not the initial empty
  // placeholder.
  const flushPendingUpdate = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    const fn = pendingUpdateRef.current;
    pendingUpdateRef.current = null;
    const session = currentSessionRef.current;
    if (session && fn) fn(session);
  }, [currentSessionRef]);

  useEffect(() => {
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  // ── Abort ──────────────────────────────────────────────────────────

  const abort = useCallback(() => {
    abortRef.current?.();
    abortRef.current = null;
  }, []);

  // ── Ensure active session (deferred creation) ──────────────────────
  // Returns the existing session, or null if a new session must be
  // created by the caller (async API call required).

  const ensureActiveSession = useCallback(
    (_message: string): ChatSession | null => {
      const existing = currentSessionRef.current;
      const model = selectedModelRef.current;
      if (!model) return null;

      // Mode was switched while session has messages → need new session
      if (existing && pendingModeSwitchRef.current && existing.messages.length > 0) {
        return null; // signal: caller must create via createSessionForMessage
      }

      // Existing session (empty or with messages, same mode) → reuse
      if (existing) return existing;

      // No session at all → caller must create
      return null;
    },
    [currentSessionRef, selectedModelRef, pendingModeSwitchRef],
  );

  // ── Send message ───────────────────────────────────────────────────

  const sendMessage = useCallback(
    async (message: string) => {
      if (isStreaming) return;

      const model = selectedModelRef.current;
      if (!model) return;

      // Resolve the active session — create on-demand if needed
      let activeSession = ensureActiveSession(message);

      if (!activeSession) {
        // Either no session exists, or mode was switched — create a new one
        pendingModeSwitchRef.current = false;
        activeSession = await createSessionRef.current(model, message);
      }

      if (!activeSession) return;

      // Cancel any existing stream
      abortRef.current?.();
      abortRef.current = null;

      // Create user message
      const userMessage: ChatMessage = {
        id: generateMessageId(),
        role: 'user',
        content: message,
        timestamp: Date.now(),
        status: 'sent',
      };

      let updatedSession = addMessageToSession(activeSession, userMessage);
      applySessionUpdate(updatedSession);

      // Create placeholder assistant message
      const assistantId = generateMessageId();
      assistantContentRef.current = '';
      const assistantMessage: ChatMessage = {
        id: assistantId,
        role: 'assistant',
        content: '',
        timestamp: Date.now(),
        status: 'sending',
        trace: activeSession.modelType === 'agent' ? null : undefined,
      };

      updatedSession = addMessageToSession(updatedSession, assistantMessage);
      applySessionUpdate(updatedSession);

      setIsStreaming(true);

      try {
        if (activeSession.modelType === 'agent') {
          abortRef.current = streamAgentChatMessage(
            activeSession.modelId,
            {
              message,
              sessionId: String(activeSession.id),
              history: buildHistory(activeSession),
            },
            {
              onEvent: (event) => {
                // Accumulate delta synchronously — the rAF throttle may drop
                // intermediate reply_delta events, so we keep a running total
                // outside the throttle so onComplete always sees the full text.
                if (event.type === 'reply_delta' && event.delta) {
                  assistantContentRef.current += event.delta;
                }
                scheduleUpdate((session) => {
                  const currentMsg = session.messages.find(
                    (m) => m.id === assistantId,
                  );
                  const nextTrace = mergeAgentTrace(
                    currentMsg?.trace ?? null,
                    event,
                    activeSession.modelId,
                  );
                  const nextContent =
                    event.type === 'reply_delta'
                      ? assistantContentRef.current
                      : event.replyText ?? (assistantContentRef.current || (currentMsg?.content ?? ''));

                  const nextStatus =
                    event.type === 'error'
                      ? 'failed'
                      : event.type === 'completed' || event.type === 'handoff'
                        ? 'sent'
                        : 'sending';

                  const nextSession = updateMessageInSession(
                    session,
                    assistantId,
                    {
                      content: nextContent,
                      status: nextStatus,
                      error: event.errorMessage ?? undefined,
                      trace: nextTrace,
                    },
                  );
                  applyTransientSessionUpdate(nextSession);
                });
              },
              onError: (error) => {
                const session = currentSessionRef.current;
                if (session) {
                  const currentMsg = session.messages.find(
                    (m) => m.id === assistantId,
                  );
                  const failedTrace = currentMsg?.trace
                    ? { ...currentMsg.trace, status: 'failed', errorMessage: error.message }
                    : undefined;
                  const nextSession = updateMessageInSession(session, assistantId, {
                    status: 'failed',
                    error: error.message,
                    trace: failedTrace,
                  });
                  applySessionUpdate(nextSession);
                }
                setIsStreaming(false);
              },
              onComplete: () => {
                // Flush any pending rAF update so we save the final content
                flushPendingUpdate();
                let session = currentSessionRef.current;
                if (session) {
                  const currentMsg = session.messages.find(
                    (m) => m.id === assistantId,
                  );
                  // If the flushed rAF applied a stale updater (e.g. the
                  // terminal "completed" event), the session may still have
                  // incomplete content.  Patch it from the synchronous
                  // accumulator before persisting.
                  if (
                    assistantContentRef.current &&
                    currentMsg?.content !== assistantContentRef.current
                  ) {
                    session = updateMessageInSession(session, assistantId, {
                      content: assistantContentRef.current,
                    });
                    applySessionUpdate(session);
                  }
                  const finalized = updateMessageInSession(session, assistantId, {
                    status: currentMsg?.status === 'failed' ? 'failed' : 'sent',
                  });
                  applySessionUpdate(finalized);

                  // Persist to server (best-effort)
                  if (isServerSessionId(session.id)) {
                    const userMsg = finalized.messages.find(
                      (m) => m.role === 'user' && m.content === message,
                    );
                    const asstMsg = finalized.messages.find(
                      (m) => m.id === assistantId,
                    );
                    if (userMsg && asstMsg) {
                      saveChatTurn(session.id, {
                        userMessage: {
                          role: 'user',
                          content: userMsg.content,
                          status: 'sent',
                        },
                        assistantMessage: {
                          role: 'assistant',
                          content: asstMsg.content,
                          status: asstMsg.status ?? 'sent',
                          errorMessage: asstMsg.error ?? null,
                          traceJson: asstMsg.trace as Record<string, unknown> ?? null,
                        },
                      }).catch(() => {
                        // Silent — localStorage cache is the fallback
                      });
                    }
                  }
                }
                setIsStreaming(false);
              },
            },
          );
        } else {
          // Model (card) mode
          abortRef.current = streamCardChatMessage(
            activeSession.modelId,
            {
              message,
              sessionId: String(activeSession.id),
            },
            {
              onChunk: accumulateStreamContent((content) => {
                assistantContentRef.current = content;
                scheduleUpdate((session) => {
                  const nextSession = updateMessageInSession(
                    session,
                    assistantId,
                    { content, status: 'sending' },
                  );
                  applyTransientSessionUpdate(nextSession);
                });
              }),
              onError: (error) => {
                const session = currentSessionRef.current;
                if (session) {
                  const nextSession = updateMessageInSession(
                    session,
                    assistantId,
                    { status: 'failed', error: error.message },
                  );
                  applySessionUpdate(nextSession);
                }
                setIsStreaming(false);
              },
              onComplete: () => {
                // Flush any pending rAF update so we save the final content
                flushPendingUpdate();
                let session = currentSessionRef.current;
                if (session) {
                  const currentMsg = session.messages.find(
                    (m) => m.id === assistantId,
                  );
                  // Same as agent mode: patch stale content from the
                  // synchronous accumulator before persisting.
                  if (
                    assistantContentRef.current &&
                    currentMsg?.content !== assistantContentRef.current
                  ) {
                    session = updateMessageInSession(session, assistantId, {
                      content: assistantContentRef.current,
                    });
                    applySessionUpdate(session);
                  }
                  const finalized = updateMessageInSession(session, assistantId, {
                    status: 'sent',
                  });
                  applySessionUpdate(finalized);

                  // Persist to server (best-effort)
                  if (isServerSessionId(session.id)) {
                    const userMsg = finalized.messages.find(
                      (m) => m.role === 'user' && m.content === message,
                    );
                    const asstMsg = finalized.messages.find(
                      (m) => m.id === assistantId,
                    );
                    if (userMsg && asstMsg) {
                      saveChatTurn(session.id, {
                        userMessage: {
                          role: 'user',
                          content: userMsg.content,
                          status: 'sent',
                        },
                        assistantMessage: {
                          role: 'assistant',
                          content: asstMsg.content,
                          status: asstMsg.status ?? 'sent',
                          errorMessage: asstMsg.error ?? null,
                        },
                      }).catch(() => {});
                    }
                  }
                }
                setIsStreaming(false);
              },
            },
          );
        }
      } catch (error) {
        const session = currentSessionRef.current;
        if (session) {
          const failedSession = updateMessageInSession(session, assistantId, {
            status: 'failed',
            error: (error as Error).message,
          });
          applySessionUpdate(failedSession);
        }
        setIsStreaming(false);
      }
    },
    [
      isStreaming,
      currentSessionRef,
      selectedModelRef,
      pendingModeSwitchRef,
      applySessionUpdate,
      applyTransientSessionUpdate,
      scheduleUpdate,
    ],
  );

  // ── Regenerate ─────────────────────────────────────────────────────

  const regenerateReply = useCallback(
    async (assistantMessageId: string) => {
      const session = currentSessionRef.current;
      if (!session) return;

      // Find the assistant message and the preceding user message
      const msgIndex = session.messages.findIndex(
        (m) => m.id === assistantMessageId,
      );
      if (msgIndex <= 0) return;

      const precedingMsg = session.messages[msgIndex - 1];
      if (precedingMsg.role !== 'user') return;

      // Remove the assistant message
      const cleanedSession: ChatSession = {
        ...session,
        messages: session.messages.filter((m) => m.id !== assistantMessageId),
      };
      applySessionUpdate(cleanedSession);

      // Re-send the user message
      await sendMessage(precedingMsg.content);
    },
    [currentSessionRef, applySessionUpdate, sendMessage],
  );

  return { isStreaming, sendMessage, abort, regenerateReply };
}
