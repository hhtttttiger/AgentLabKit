import { describe, expect, it } from 'vitest';
import { mergeAgentTrace, buildStepFromEvent, buildHistory, findLatestTraceMessageId } from './agent-trace-merge';
import type { AgentStreamEvent } from './contracts';

const baseEvent: AgentStreamEvent = {
  type: 'context',
  runId: 'run-1',
  sessionId: 'session-1',
  traceId: 'trace-1',
  agentKey: 'agent-a',
  agentVersion: 3,
};

describe('buildStepFromEvent', () => {
  it('returns context step', () => {
    const step = buildStepFromEvent({ ...baseEvent, type: 'context', appliedSkills: [] });
    expect(step).toEqual({
      type: 'context',
      status: 'ready',
      title: 'Agent context ready',
      appliedSkills: [],
    });
  });

  it('returns tool_call step', () => {
    const step = buildStepFromEvent({
      ...baseEvent,
      type: 'tool_call',
      toolEvent: { toolName: 'read_file', status: 'started', arguments: {}, tags: [] },
    });
    expect(step?.type).toBe('tool_call');
    expect(step?.status).toBe('running');
  });

  it('returns tool_result step with error message', () => {
    const step = buildStepFromEvent({
      ...baseEvent,
      type: 'tool_result',
      toolEvent: {
        toolName: 'search',
        status: 'failed',
        arguments: {},
        errorMessage: 'timeout',
        tags: [],
      },
    });
    expect(step?.type).toBe('tool_result');
    expect(step?.message).toBe('timeout');
  });

  it('returns delegation_delta step', () => {
    const step = buildStepFromEvent({
      ...baseEvent,
      type: 'delegation_delta',
      delta: 'thinking...',
      delegationAgentKey: 'sub-agent',
    });
    expect(step?.type).toBe('delegation_delta');
    expect(step?.delta).toBe('thinking...');
  });

  it('returns handoff step', () => {
    const step = buildStepFromEvent({
      ...baseEvent,
      type: 'handoff',
      replyText: 'transferred',
      handoffReason: 'escalation',
    });
    expect(step?.type).toBe('handoff');
    expect(step?.handoffReason).toBe('escalation');
  });

  it('returns reply_completed step', () => {
    const step = buildStepFromEvent({
      ...baseEvent,
      type: 'completed',
      replyText: 'done',
    });
    expect(step?.type).toBe('reply_completed');
  });

  it('returns error step', () => {
    const step = buildStepFromEvent({
      ...baseEvent,
      type: 'error',
      errorMessage: 'failed',
      status: 'failed',
    });
    expect(step?.type).toBe('error');
    expect(step?.message).toBe('failed');
  });

  it('returns null for unknown type', () => {
    const step = buildStepFromEvent({ ...baseEvent, type: 'reply_delta' });
    expect(step).toBeNull();
  });
});

describe('mergeAgentTrace', () => {
  it('creates initial trace from context event', () => {
    const trace = mergeAgentTrace(null, baseEvent, 'fallback');
    expect(trace.runId).toBe('run-1');
    expect(trace.agentKey).toBe('agent-a');
    expect(trace.status).toBe('running');
    expect(trace.steps).toHaveLength(1);
  });

  it('accumulates reply text from delta events', () => {
    let trace = mergeAgentTrace(null, baseEvent, 'fallback');
    trace = mergeAgentTrace(trace, {
      ...baseEvent,
      type: 'reply_delta',
      delta: 'Hello ',
    }, 'fallback');
    expect(trace.replyText).toBe('Hello ');

    trace = mergeAgentTrace(trace, {
      ...baseEvent,
      type: 'reply_delta',
      delta: 'world',
    }, 'fallback');
    expect(trace.replyText).toBe('Hello world');
  });

  it('uses replyText from completed event', () => {
    let trace = mergeAgentTrace(null, baseEvent, 'fallback');
    trace = mergeAgentTrace(trace, {
      ...baseEvent,
      type: 'completed',
      replyText: 'final answer',
      usage: { totalTokens: 42 },
    }, 'fallback');
    expect(trace.replyText).toBe('final answer');
    expect(trace.usage?.totalTokens).toBe(42);
  });

  it('appends tool events', () => {
    let trace = mergeAgentTrace(null, baseEvent, 'fallback');
    const toolEvent = { toolName: 'search', status: 'success', arguments: {}, tags: [] };
    trace = mergeAgentTrace(trace, {
      ...baseEvent,
      type: 'tool_result',
      toolEvent,
    }, 'fallback');
    expect(trace.toolEvents).toHaveLength(1);
  });

  it('falls back to fallbackAgentKey when event has none', () => {
    const trace = mergeAgentTrace(null, {
      ...baseEvent,
      agentKey: undefined,
    }, 'fallback-key');
    expect(trace.agentKey).toBe('fallback-key');
  });
});

describe('buildHistory', () => {
  it('filters to user and assistant messages only', () => {
    const history = buildHistory({
      messages: [
        { role: 'user', content: 'hi' },
        { role: 'assistant', content: 'hello' },
        { role: 'system', content: 'prompt' },
      ],
    });
    expect(history).toEqual([
      { role: 'user', content: 'hi' },
      { role: 'assistant', content: 'hello' },
    ]);
  });
});

describe('findLatestTraceMessageId', () => {
  it('returns the last message with a trace', () => {
    const id = findLatestTraceMessageId({
      messages: [
        { id: 'a', trace: { runId: 'r1' } },
        { id: 'b' },
        { id: 'c', trace: { runId: 'r2' } },
      ],
    });
    expect(id).toBe('c');
  });

  it('returns null when no message has trace', () => {
    const id = findLatestTraceMessageId({
      messages: [{ id: 'a' }, { id: 'b' }],
    });
    expect(id).toBeNull();
  });
});
