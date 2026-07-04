/**
 * AI Chat Module - API Layer
 */

import { apiRequest, buildApiUrl, handleUnauthorized } from '@/shared/api/client';
import { ApiError } from '@/shared/api/errors';
import i18n from '@/shared/i18n';
import { getStoredToken } from '@/shared/auth/storage';
import type {
  AgentStreamCallbacks,
  AgentStreamEvent,
  AgentStreamEventType,
  AiInvokeResultDto,
  ChatRequest,
  ChatMessageDto,
  ChatSessionDto,
  ModelOption,
  SaveTurnRequest,
  SaveTurnResponse,
  StreamCallbacks,
  StreamChunk,
} from './lib/contracts';

type ModelOptionDto = {
  modelKey: string;
  displayName: string;
  isEnabled: boolean;
};

type AgentOptionDto = {
  agentKey: string;
  displayName: string;
  publishedVersionNumber: number;
};

export async function listChatModelOptions(): Promise<ModelOption[]> {
  const options = await apiRequest<ModelOptionDto[]>('/api/llm-catalog/options/models');

  return options
    .filter((option) => option.isEnabled)
    .map((option) => ({
      id: option.modelKey,
      name: option.displayName,
      type: 'model' as const,
    }));
}

export async function listChatAgentOptions(): Promise<ModelOption[]> {
  const options = await apiRequest<AgentOptionDto[]>('/api/ai/invoke/agents/options');

  return options.map((option) => ({
    id: option.agentKey,
    name: option.displayName,
    type: 'agent' as const,
    description: `Published v${option.publishedVersionNumber}`,
    publishedVersionNumber: option.publishedVersionNumber,
  }));
}

export async function sendChatMessage(
  modelId: string,
  request: ChatRequest
): Promise<AiInvokeResultDto> {
  const url = buildApiUrl(`/api/ai/invoke/${modelId}/text`);
  const token = getStoredToken();

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    },
    body: JSON.stringify({
      Message: request.message,
      SystemPrompt: request.systemPrompt,
      InvocationContext: request.sessionId
        ? { SessionId: request.sessionId }
        : undefined,
    }),
  });

  if (!response.ok) {
    if (handleUnauthorized(response)) {
      throw new ApiError(i18n.t('api.sessionExpired'), 401);
    }
    const errorText = await response.text();
    throw new Error(`Failed to send message: ${response.status} ${errorText || response.statusText}`);
  }

  return (await response.json()) as AiInvokeResultDto;
}

export function streamCardChatMessage(
  modelId: string,
  request: ChatRequest,
  callbacks: StreamCallbacks
): () => void {
  return streamSse(buildApiUrl(`/api/ai/invoke/${modelId}/text/stream`), {
    Message: request.message,
    SystemPrompt: request.systemPrompt,
    InvocationContext: request.sessionId
      ? { SessionId: request.sessionId }
      : undefined,
  }, {
    onEvent: (payload) => {
      const chunk = payload as StreamChunk;
      callbacks.onChunk(chunk);
      if (chunk.done) {
        callbacks.onComplete();
      }
    },
    onError: callbacks.onError,
    onComplete: callbacks.onComplete,
  });
}

export function streamAgentChatMessage(
  agentKey: string,
  request: ChatRequest,
  callbacks: AgentStreamCallbacks
): () => void {
  return streamSse(buildApiUrl(`/api/ai/invoke/agents/${agentKey}/turn/stream`), {
    Message: request.message,
    SessionId: request.sessionId,
    History: (request.history ?? []).map((item) => ({
      Role: item.role,
      Content: item.content,
      Name: item.name,
      Metadata: item.metadata,
    })),
  }, {
    onEvent: (payload) => callbacks.onEvent(payload as AgentStreamEvent),
    onError: callbacks.onError,
    onComplete: callbacks.onComplete,
  });
}

function streamSse(
  url: string,
  body: unknown,
  callbacks: {
    onEvent: (payload: unknown) => void;
    onError: (error: Error) => void;
    onComplete: () => void;
  }
): () => void {
  const controller = new AbortController();
  const token = getStoredToken();
  let buffer = '';
  let completed = false;

  fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    },
    body: JSON.stringify(body),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        if (handleUnauthorized(response)) {
          throw new ApiError(i18n.t('api.sessionExpired'), 401);
        }
        const errorText = await response.text();
        throw new Error(`Failed to stream message: ${response.status} ${errorText || response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Response body is not readable');
      }

      const decoder = new TextDecoder();

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            if (!completed) {
              completed = true;
              callbacks.onComplete();
            }
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const parsed = extractSsePayloads(buffer);
          buffer = parsed.remaining;

          for (const payload of parsed.payloads) {
            callbacks.onEvent(payload);
            if (isTerminalAgentEvent(payload) && !completed) {
              completed = true;
              callbacks.onComplete();
            }
          }

          if (parsed.isDone && !completed) {
            completed = true;
            callbacks.onComplete();
          }
        }
      } finally {
        reader.releaseLock();
      }
    })
    .catch((error) => {
      if (error.name === 'AbortError') {
        return;
      }

      callbacks.onError(error as Error);
    });

  return () => controller.abort();
}

export function accumulateStreamContent(
  onContent: (content: string) => void
): (chunk: StreamChunk) => void {
  let content = '';

  return (chunk: StreamChunk) => {
    content += chunk.content;
    onContent(content);
  };
}

export function extractStreamMessages(buffer: string): {
  chunks: StreamChunk[];
  remaining: string;
  isComplete: boolean;
} {
  const parsed = extractSsePayloads(buffer);
  const chunks = parsed.payloads.filter(isStreamChunk);

  return {
    chunks,
    remaining: parsed.remaining,
    isComplete: parsed.isDone || chunks.some((chunk) => chunk.done),
  };
}

export function extractAgentStreamEvents(buffer: string): {
  events: AgentStreamEvent[];
  remaining: string;
  isComplete: boolean;
} {
  const parsed = extractSsePayloads(buffer);
  const events = parsed.payloads.filter(isAgentStreamEvent);

  return {
    events,
    remaining: parsed.remaining,
    isComplete: parsed.isDone || events.some(isTerminalAgentEvent),
  };
}

function extractSsePayloads(buffer: string): {
  payloads: unknown[];
  remaining: string;
  isDone: boolean;
} {
  const lines = buffer.split('\n');
  const remaining = lines.pop() || '';
  const payloads: unknown[] = [];

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line || !line.startsWith('data: ')) {
      continue;
    }

    const data = line.slice(6);
    if (data === '[DONE]') {
      return {
        payloads,
        remaining: '',
        isDone: true,
      };
    }

    try {
      payloads.push(JSON.parse(data));
    } catch (parseError) {
      console.error('Failed to parse SSE chunk:', parseError, line);
    }
  }

  return {
    payloads,
    remaining,
    isDone: false,
  };
}

function isStreamChunk(payload: unknown): payload is StreamChunk {
  return typeof payload === 'object'
    && payload !== null
    && 'content' in payload
    && 'done' in payload;
}

function isAgentStreamEvent(payload: unknown): payload is AgentStreamEvent {
  return typeof payload === 'object'
    && payload !== null
    && 'type' in payload
    && 'runId' in payload;
}

function isTerminalAgentEvent(payload: unknown): boolean {
  if (!isAgentStreamEvent(payload)) return false;
  const terminalTypes: readonly AgentStreamEventType[] = ['completed', 'handoff', 'error'];
  return terminalTypes.includes(payload.type);
}

// ──────────────────────────────────────────────────────────────────────
// Session CRUD (API is source of truth, localStorage is cache)
// ──────────────────────────────────────────────────────────────────────

export async function fetchChatSessions(
  page: number = 1,
  pageSize: number = 50,
): Promise<{ items: ChatSessionDto[]; total: number; page: number; pageSize: number }> {
  return apiRequest('/api/chat/sessions', { query: { page, pageSize } });
}

export async function createChatSession(
  data: { title: string; modelType: string; modelId: string },
): Promise<ChatSessionDto> {
  return apiRequest('/api/chat/sessions', {
    method: 'POST',
    body: { title: data.title, modelType: data.modelType, modelId: data.modelId },
  });
}

export async function getChatSession(sessionId: number | string): Promise<ChatSessionDto> {
  return apiRequest(`/api/chat/sessions/${sessionId}`);
}

export async function updateChatSession(
  sessionId: number | string,
  data: { title?: string },
): Promise<ChatSessionDto> {
  return apiRequest(`/api/chat/sessions/${sessionId}`, {
    method: 'PATCH',
    body: data,
  });
}

export async function deleteChatSession(sessionId: number | string): Promise<void> {
  return apiRequest(`/api/chat/sessions/${sessionId}`, { method: 'DELETE' });
}

export async function fetchChatMessages(
  sessionId: number | string,
  cursor?: number,
  limit: number = 50,
): Promise<{ messages: ChatMessageDto[]; hasMore: boolean }> {
  return apiRequest(`/api/chat/sessions/${sessionId}/messages`, {
    query: { ...(cursor ? { cursor } : {}), limit },
  });
}

export async function saveChatTurn(
  sessionId: number | string,
  data: SaveTurnRequest,
): Promise<SaveTurnResponse> {
  return apiRequest(`/api/chat/sessions/${sessionId}/messages/save-turn`, {
    method: 'POST',
    body: data,
  });
}
