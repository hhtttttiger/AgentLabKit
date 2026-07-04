import { describe, expect, it } from 'vitest';
import {
  accumulateStreamContent,
  extractAgentStreamEvents,
  extractStreamMessages,
} from './api';

describe('extractStreamMessages', () => {
  it('parses complete SSE lines and preserves the trailing partial buffer', () => {
    const result = extractStreamMessages(
      'data: {"content":"Hel","done":false}\n' +
      'data: {"content":"lo","done":false}\n' +
      'data: {"content":"wor',
    );

    expect(result.chunks).toEqual([
      { content: 'Hel', done: false },
      { content: 'lo', done: false },
    ]);
    expect(result.remaining).toBe('data: {"content":"wor');
    expect(result.isComplete).toBe(false);
  });

  it('marks the stream complete when a final chunk or done sentinel arrives', () => {
    expect(
      extractStreamMessages('data: {"content":"done","done":true}\n'),
    ).toMatchObject({
      chunks: [{ content: 'done', done: true }],
      isComplete: true,
    });

    expect(
      extractStreamMessages('data: [DONE]\n'),
    ).toMatchObject({
      chunks: [],
      remaining: '',
      isComplete: true,
    });
  });
});

describe('accumulateStreamContent', () => {
  it('accumulates streamed fragments into one message body', () => {
    const snapshots: string[] = [];
    const onChunk = accumulateStreamContent((content) => snapshots.push(content));

    onChunk({ content: 'Hello', done: false });
    onChunk({ content: ' world', done: false });

    expect(snapshots).toEqual(['Hello', 'Hello world']);
  });
});

describe('extractAgentStreamEvents', () => {
  it('parses agent SSE events and recognizes terminal events', () => {
    const result = extractAgentStreamEvents(
      'data: {"type":"context","runId":"run-1","sessionId":"session-1","traceId":"trace-1"}\n' +
      'data: {"type":"tool_result","runId":"run-1","sessionId":"session-1","traceId":"trace-1"}\n' +
      'data: {"type":"completed","runId":"run-1","sessionId":"session-1","traceId":"trace-1"}\n',
    );

    expect(result.events.map((event) => event.type)).toEqual(['context', 'tool_result', 'completed']);
    expect(result.isComplete).toBe(true);
    expect(result.remaining).toBe('');
  });
});
