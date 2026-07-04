/**
 * Model Test Dialog - streaming client for the diagnostic test endpoint.
 *
 * 调用 `POST /api/ai/invoke/{modelId}/text/test-stream`，解析 content / stats / error
 * 三类 SSE 事件。自建精简 SSE reader（不跨模块依赖 ai-chat 的私有 streamSse）。
 */

import { buildApiUrl, handleUnauthorized } from '@/shared/api/client';
import { ApiError } from '@/shared/api/errors';
import i18n from '@/shared/i18n';
import { getStoredToken } from '@/shared/auth/storage';
import type { EmbeddingTestResult, ModelTestStreamCallbacks, ModelTestStreamEvent } from './test-types';

export interface ModelTestRequest {
  message: string;
  systemPrompt?: string;
}

export function streamModelTest(
  modelId: string,
  request: ModelTestRequest,
  callbacks: ModelTestStreamCallbacks,
): () => void {
  const controller = new AbortController();
  const token = getStoredToken();
  let buffer = '';
  let completed = false;

  const finish = () => {
    if (!completed) {
      completed = true;
      callbacks.onComplete();
    }
  };

  fetch(buildApiUrl(`/api/ai/invoke/${modelId}/text/test-stream`), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    },
    body: JSON.stringify({
      Message: request.message,
      SystemPrompt: request.systemPrompt,
    }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        if (handleUnauthorized(response)) {
          throw new ApiError(i18n.t('api.sessionExpired'), 401);
        }
        const errorText = await response.text();
        throw new Error(`Failed to stream test: ${response.status} ${errorText || response.statusText}`);
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
            finish();
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const parsed = extractSseEvents(buffer);
          buffer = parsed.remaining;

          for (const event of parsed.events) {
            dispatchEvent(event, callbacks);
          }

          if (parsed.isDone) {
            finish();
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
      callbacks.onError({ errorMessage: (error as Error).message });
      finish();
    });

  return () => controller.abort();
}

function dispatchEvent(event: ModelTestStreamEvent | null, callbacks: ModelTestStreamCallbacks): void {
  if (!event) {
    return;
  }
  if (event.type === 'content') {
    callbacks.onContent(event.content, {
      instanceKey: event.instance_key ?? undefined,
      provider: event.provider ?? undefined,
      model: event.model ?? undefined,
    });
  } else if (event.type === 'stats') {
    callbacks.onStats({
      instanceKey: event.instance_key ?? undefined,
      provider: event.provider ?? undefined,
      model: event.model ?? undefined,
      ttftMs: event.ttft_ms,
      totalMs: event.total_ms,
      finishReason: event.finish_reason,
      inputTokens: event.input_tokens,
      outputTokens: event.output_tokens,
      totalTokens: event.total_tokens,
    });
  } else if (event.type === 'error') {
    callbacks.onError({
      errorMessage: event.message,
      errorCode: event.code ?? null,
      ttftMs: event.ttft_ms,
      totalMs: event.total_ms,
    });
  }
}

function extractSseEvents(buffer: string): {
  events: (ModelTestStreamEvent | null)[];
  remaining: string;
  isDone: boolean;
} {
  const lines = buffer.split('\n');
  const remaining = lines.pop() || '';
  const events: (ModelTestStreamEvent | null)[] = [];
  let isDone = false;

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line || !line.startsWith('data: ')) {
      continue;
    }
    const data = line.slice(6);
    if (data === '[DONE]') {
      isDone = true;
      continue;
    }
    try {
      events.push(JSON.parse(data) as ModelTestStreamEvent);
    } catch (parseError) {
      console.error('Failed to parse model test SSE chunk:', parseError, line);
    }
  }

  return { events, remaining, isDone };
}

/** Embedding 模型测试 —— 单次请求，返回向量结果及诊断信息。 */
export interface EmbeddingTestRequest {
  text: string;
  dimensions?: number;
}

export async function testEmbedding(
  modelId: string,
  request: EmbeddingTestRequest,
  signal?: AbortSignal,
): Promise<EmbeddingTestResult> {
  const token = getStoredToken();

  const response = await fetch(buildApiUrl(`/api/ai/invoke/${modelId}/embedding/test`), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    },
    body: JSON.stringify({
      Text: request.text,
      Dimensions: request.dimensions,
    }),
    signal,
  });

  if (!response.ok) {
    if (handleUnauthorized(response)) {
      throw new ApiError(i18n.t('api.sessionExpired'), 401);
    }
    const errorText = await response.text();
    throw new Error(`Embedding test failed: ${response.status} ${errorText || response.statusText}`);
  }

  const data = await response.json();
  return data.data as EmbeddingTestResult;
}
