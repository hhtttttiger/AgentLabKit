import { buildApiUrl, getApiHeaders } from '@/shared/api/client';

export type ConversationStreamEvent = { type?: string; runId?: string; delta?: string | null; replyText?: string | null; errorMessage?: string | null };

export function streamConversationMessage(conversationId: string, message: string, callbacks: {
  onEvent: (event: ConversationStreamEvent) => void;
  onError: (error: Error) => void;
  onComplete: () => void;
}): () => void {
  const controller = new AbortController();
  fetch(buildApiUrl(`/api/conversations/${conversationId}/messages/stream`), {
    method: 'POST', headers: getApiHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ message }), signal: controller.signal,
  }).then(async (response) => {
    if (!response.ok) throw new Error(`Failed to stream conversation: ${response.status}`);
    const reader = response.body?.getReader();
    if (!reader) throw new Error('Response body is not readable');
    const decoder = new TextDecoder(); let buffer = '';
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split('\n\n'); buffer = frames.pop() ?? '';
        for (const frame of frames) {
          const line = frame.split('\n').find((item) => item.startsWith('data: '));
          if (!line) continue;
          const payload = line.slice(6);
          if (payload === '[DONE]') continue;
          callbacks.onEvent(JSON.parse(payload) as ConversationStreamEvent);
        }
      }
    } finally { reader.releaseLock(); }
    callbacks.onComplete();
  }).catch((error) => { if ((error as Error).name !== 'AbortError') callbacks.onError(error as Error); });
  return () => controller.abort();
}
