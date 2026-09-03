import { describe, it, expect } from 'vitest';
import { mapTraceToAgentExecution } from './traceMapper';
import type { TraceDetailResponse, SpanData } from '@/modules/observability/lib/contracts';

describe('traceMapper', () => {
  const mockSpan: SpanData = {
    spanId: 'span-1',
    traceId: 'trace-1',
    parentSpanId: null,
    name: 'agent.run',
    kind: 'agent',
    status: 'ok',
    instrumentationScope: 'test',
    startedAtUtc: '2024-01-01T00:00:00Z',
    completedAtUtc: '2024-01-01T00:00:01Z',
    durationMs: 1000,
    attributes: {
      'agent.key': 'test-agent',
      'agent.version': 2,
      'session.id': 'session-123',
      'agent.action': 'reply',
      'agent.applied_skills': [],
    },
    events: [],
    links: [],
    errorCode: null,
    errorMessage: null,
  };

  const mockToolSpan: SpanData = {
    spanId: 'span-2',
    traceId: 'trace-1',
    parentSpanId: 'span-1',
    name: 'web_search',
    kind: 'tool',
    status: 'ok',
    instrumentationScope: 'test',
    startedAtUtc: '2024-01-01T00:00:00.100Z',
    completedAtUtc: '2024-01-01T00:00:00.500Z',
    durationMs: 400,
    attributes: {
      'tool.name': 'web_search',
      'tool.display_name': 'Web Search',
      'tool.arguments': { query: 'test' },
      'tool.output': 'Search results',
      'tool.tags': ['search'],
    },
    events: [],
    links: [],
    errorCode: null,
    errorMessage: null,
  };

  const mockLlmSpan: SpanData = {
    spanId: 'span-3',
    traceId: 'trace-1',
    parentSpanId: 'span-1',
    name: 'openai.chat',
    kind: 'llm',
    status: 'ok',
    instrumentationScope: 'test',
    startedAtUtc: '2024-01-01T00:00:00.200Z',
    completedAtUtc: '2024-01-01T00:00:00.800Z',
    durationMs: 600,
    attributes: {
      'llm.output_text': 'Hello world',
    },
    events: [],
    links: [],
    errorCode: null,
    errorMessage: null,
  };

  const mockDetail: TraceDetailResponse = {
    trace: {
      traceId: 'trace-1',
      rootSpanId: 'span-1',
      runId: 'run-123',
      agentKey: 'test-agent',
      sessionId: 'session-123',
      userId: null,
      correlationId: null,
      status: 'ok',
      totalDurationMs: 1000,
      totalInputTokens: 100,
      totalOutputTokens: 50,
      cacheWriteTokens: 0,
      cacheReadTokens: 0,
      totalEstimatedCost: 0.001,
      spanCount: 3,
      droppedSpanCount: 0,
      sampleReason: 'test',
      attributes: {},
      schemaVersion: 1,
      startedAtUtc: '2024-01-01T00:00:00Z',
      completedAtUtc: '2024-01-01T00:00:01Z',
    },
    spans: [mockSpan, mockToolSpan, mockLlmSpan],
  };

  it('maps trace metadata to AgentExecutionTrace', () => {
    const result = mapTraceToAgentExecution(mockDetail);

    expect(result.runId).toBe('run-123');
    expect(result.traceId).toBe('trace-1');
    expect(result.sessionId).toBe('session-123');
    expect(result.agentKey).toBe('test-agent');
    expect(result.agentVersion).toBe(2);
    expect(result.status).toBe('succeeded');
    expect(result.action).toBe('reply');
  });

  it('maps spans to steps', () => {
    const result = mapTraceToAgentExecution(mockDetail);

    expect(result.steps).toHaveLength(3);
    expect(result.steps[0].type).toBe('context');
    expect(result.steps[0].title).toBe('agent.run');
    expect(result.steps[1].type).toBe('tool_call');
    expect(result.steps[1].title).toBe('Web Search');
    expect(result.steps[2].type).toBe('reply_completed');
    expect(result.steps[2].title).toBe('openai.chat');
  });

  it('extracts tool events from tool spans', () => {
    const result = mapTraceToAgentExecution(mockDetail);

    expect(result.toolEvents).toHaveLength(1);
    expect(result.toolEvents[0].toolName).toBe('web_search');
    expect(result.toolEvents[0].displayName).toBe('Web Search');
    expect(result.toolEvents[0].status).toBe('succeeded');
    expect(result.toolEvents[0].arguments).toEqual({ query: 'test' });
    expect(result.toolEvents[0].outputText).toBe('Search results');
    expect(result.toolEvents[0].tags).toEqual(['search']);
    expect(result.toolEvents[0].durationMs).toBe(400);
  });

  it('calculates usage from trace totals', () => {
    const result = mapTraceToAgentExecution(mockDetail);

    expect(result.usage).toEqual({
      inputTokens: 100,
      outputTokens: 50,
      totalTokens: 150,
    });
  });

  it('handles error spans', () => {
    const errorSpan: SpanData = {
      ...mockToolSpan,
      spanId: 'span-error',
      status: 'error',
      errorMessage: 'Tool failed',
    };
    const detailWithError: TraceDetailResponse = {
      ...mockDetail,
      spans: [errorSpan],
    };

    const result = mapTraceToAgentExecution(detailWithError);

    expect(result.steps[0].status).toBe('failed');
    expect(result.toolEvents[0].status).toBe('failed');
    expect(result.toolEvents[0].errorMessage).toBe('Tool failed');
  });

  it('handles trace with error status', () => {
    const errorDetail: TraceDetailResponse = {
      ...mockDetail,
      trace: { ...mockDetail.trace, status: 'error' },
    };

    const result = mapTraceToAgentExecution(errorDetail);
    expect(result.status).toBe('error');
  });

  it('handles empty spans', () => {
    const emptyDetail: TraceDetailResponse = {
      ...mockDetail,
      spans: [],
    };

    const result = mapTraceToAgentExecution(emptyDetail);

    expect(result.steps).toHaveLength(0);
    expect(result.toolEvents).toHaveLength(0);
  });

  it('uses trace agentKey when span attributes missing', () => {
    const spanWithoutAttrs: SpanData = {
      ...mockSpan,
      attributes: {},
    };
    const detailWithoutAttrs: TraceDetailResponse = {
      ...mockDetail,
      spans: [spanWithoutAttrs],
    };

    const result = mapTraceToAgentExecution(detailWithoutAttrs);
    expect(result.agentKey).toBe('test-agent');
    expect(result.sessionId).toBe('session-123');
  });

  it('defaults agentVersion to 0 when missing', () => {
    const spanWithoutVersion: SpanData = {
      ...mockSpan,
      attributes: { 'agent.key': 'test-agent' },
    };
    const detailWithoutVersion: TraceDetailResponse = {
      ...mockDetail,
      spans: [spanWithoutVersion],
    };

    const result = mapTraceToAgentExecution(detailWithoutVersion);
    expect(result.agentVersion).toBeNull();
  });

  it('skips non-agent spans', () => {
    const internalSpan: SpanData = {
      ...mockSpan,
      spanId: 'span-internal',
      kind: 'internal',
      name: 'internal.span',
    };
    const detailWithInternal: TraceDetailResponse = {
      ...mockDetail,
      spans: [mockSpan, internalSpan],
    };

    const result = mapTraceToAgentExecution(detailWithInternal);
    expect(result.steps).toHaveLength(1);
    expect(result.steps[0].title).toBe('agent.run');
  });

  it('includes startedAtUtc and completedAtUtc', () => {
    const result = mapTraceToAgentExecution(mockDetail);

    expect(result.startedAtUtc).toBe('2024-01-01T00:00:00Z');
    expect(result.completedAtUtc).toBe('2024-01-01T00:00:01Z');
  });
});
