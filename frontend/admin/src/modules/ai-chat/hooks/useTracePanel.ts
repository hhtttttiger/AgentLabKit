/**
 * AI Chat Module — useTracePanel Hook
 * Trace selection and computed current trace.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ChatSession } from '../lib/contracts';
import { findLatestTraceMessageId } from '../lib/agent-trace-merge';

export function useTracePanel(currentSession: ChatSession | null) {
  const [selectedTraceMessageId, setSelectedTraceMessageId] = useState<string | null>(null);

  // Auto-select latest trace on session change
  useEffect(() => {
    if (currentSession) {
      setSelectedTraceMessageId(findLatestTraceMessageId(currentSession));
    } else {
      setSelectedTraceMessageId(null);
    }
  }, [currentSession?.id]);

  const toggleTrace = useCallback((messageId: string) => {
    setSelectedTraceMessageId((prev) => (prev === messageId ? null : messageId));
  }, []);

  const currentTrace = useMemo(() => {
    if (!currentSession) return null;

    const selected = currentSession.messages.find(
      (m) => m.id === selectedTraceMessageId,
    );
    if (selected?.trace) return selected.trace;

    const latest = [...currentSession.messages]
      .reverse()
      .find((m) => m.trace);
    return latest?.trace ?? null;
  }, [currentSession, selectedTraceMessageId]);

  return { selectedTraceMessageId, currentTrace, toggleTrace };
}
