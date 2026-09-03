/**
 * AI Chat Module — Main Chat Page
 * Composes useChatSession, useChatStream, useTracePanel hooks.
 *
 * Session lifecycle:
 *   1. Page load → fetch existing sessions, no auto-creation.
 *   2. "New Chat" button → clears current session (no server call).
 *   3. First message → server-side session is created on-demand.
 *   4. Mode switch (model ↔ agent) after messages exist → deferred:
 *      a flag is set, and the *next* sendMessage creates a new session.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ChatSession, ModelOption } from '../lib/contracts';
import { buildSessionTitle } from '../lib/session-title';
import { useChatSession } from '../hooks/useChatSession';
import { useChatStream } from '../hooks/useChatStream';
import { useTracePanel } from '../hooks/useTracePanel';
import { PlaygroundShell } from '../components/PlaygroundShell';

type AiChatPageProps = {
  agentOptions: ModelOption[];
  modelOptions: ModelOption[];
};

export function AiChatPage({ agentOptions, modelOptions }: AiChatPageProps) {
  // ── Model selection ────────────────────────────────────────────────

  const defaultModel = useMemo<ModelOption | null>(() => {
    return agentOptions[0] ?? modelOptions[0] ?? null;
  }, [agentOptions, modelOptions]);

  const [selectedModel, setSelectedModel] = useState<ModelOption | null>(defaultModel);
  const selectedModelRef = useRef<ModelOption | null>(selectedModel);

  useEffect(() => {
    if (!selectedModel && defaultModel) {
      setSelectedModel(defaultModel);
    }
  }, [defaultModel, selectedModel]);

  useEffect(() => {
    selectedModelRef.current = selectedModel;
  }, [selectedModel]);

  // ── Deferred mode-switch flag ──────────────────────────────────────
  // Set when the user switches model/agent while the current session
  // already has messages.  Consumed by useChatStream.sendMessage to
  // create a *new* session only when the next message is actually sent.

  const pendingModeSwitchRef = useRef(false);

  // ── Hooks ──────────────────────────────────────────────────────────

  const {
    sessions,
    currentSession,
    isLoadingMessages,
    currentSessionRef,
    selectSession,
    resetCurrentSession,
    createSessionForMessage,
    deleteSession,
    applySessionUpdate,
    applyTransientSessionUpdate,
  } = useChatSession(selectedModel);

  const { selectedTraceMessageId, currentTrace, toggleTrace } = useTracePanel(currentSession);

  const { isStreaming, sendMessage, abort, regenerateReply } = useChatStream(
    currentSessionRef,
    applySessionUpdate,
    applyTransientSessionUpdate,
    selectedModelRef,
    pendingModeSwitchRef,
    createSessionForMessage,
  );

  // ── Model select → deferred switch ─────────────────────────────────

  const handleSelectModel = useCallback((model: ModelOption) => {
    setSelectedModel(model);

    const session = currentSessionRef.current;
    if (!session) return;

    if (session.messages.length === 0) {
      // Empty session — update in-place, no new session needed
      applySessionUpdate({
        ...session,
        modelType: model.type,
        modelId: model.id,
        title: buildSessionTitle(model.name, ''),
      });
      return;
    }

    // Session has messages — defer new-session creation until next send
    pendingModeSwitchRef.current = true;
  }, [applySessionUpdate, currentSessionRef]);

  // ── Session select ─────────────────────────────────────────────────

  const handleSelectSession = useCallback((session: ChatSession) => {
    // Selecting an existing session cancels any pending mode switch
    pendingModeSwitchRef.current = false;
    selectSession(session);
    const matchingModel = [...agentOptions, ...modelOptions].find(
      (m) => m.type === session.modelType && m.id === session.modelId,
    );
    if (matchingModel) setSelectedModel(matchingModel);
  }, [agentOptions, modelOptions, selectSession]);

  // ── New Chat — just clear, no server creation ──────────────────────

  const handleNewChat = useCallback(() => {
    pendingModeSwitchRef.current = false;
    resetCurrentSession();
  }, [resetCurrentSession]);

  // ── Render ─────────────────────────────────────────────────────────

  return (
    <PlaygroundShell
      sessions={sessions}
      currentSession={currentSession}
      isLoadingMessages={isLoadingMessages}
      selectedTraceMessageId={selectedTraceMessageId}
      agentOptions={agentOptions}
      modelOptions={modelOptions}
      selectedModel={selectedModel}
      isStreaming={isStreaming}
      onSelectSession={handleSelectSession}
      onDeleteSession={deleteSession}
      onNewChat={handleNewChat}
      onSelectTrace={toggleTrace}
      onRegenerate={regenerateReply}
      onSend={sendMessage}
      onStop={abort}
      onSelectModel={handleSelectModel}
      currentTrace={currentSession?.modelType === 'agent' ? currentTrace : null}
    />
  );
}
