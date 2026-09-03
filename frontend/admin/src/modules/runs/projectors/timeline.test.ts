import { describe, it, expect } from 'vitest';
import { canPair, projectRunTimeline } from './timeline';
import type { RunEvent } from '../types';

describe('projectRunTimeline', () => {
  const createEvent = (overrides: Partial<RunEvent> = {}): RunEvent => ({
    id: 'event-1',
    sequence: 1,
    type: 'llm_call',
    timestamp: '2024-01-01T00:00:00Z',
    spanId: 'span-1',
    payload: {},
    metadata: {},
    ...overrides,
  });

  it('returns empty array for empty events', () => {
    expect(projectRunTimeline([])).toEqual([]);
  });

  it('sorts events by sequence number', () => {
    const events = [
      createEvent({ id: 'e2', sequence: 2 }),
      createEvent({ id: 'e1', sequence: 1 }),
      createEvent({ id: 'e3', sequence: 3 }),
    ];

    const timeline = projectRunTimeline(events);
    expect(timeline.map((t) => t.id)).toEqual(['e1', 'e2', 'e3']);
  });

  it('classifies LLM events correctly', () => {
    const events = [
      createEvent({ type: 'llm_call' }),
      createEvent({ id: 'e2', type: 'model_response', sequence: 2 }),
      createEvent({ id: 'e3', type: 'completion', sequence: 3 }),
    ];

    const timeline = projectRunTimeline(events);
    expect(timeline[0].type).toBe('llm');
    expect(timeline[1].type).toBe('llm');
    expect(timeline[2].type).toBe('llm');
  });

  it('classifies tool events correctly', () => {
    const events = [
      createEvent({ type: 'tool_call' }),
      createEvent({ id: 'e2', type: 'function_call', sequence: 2 }),
    ];

    const timeline = projectRunTimeline(events);
    expect(timeline[0].type).toBe('tool');
    expect(timeline[1].type).toBe('tool');
  });

  it('classifies error events correctly', () => {
    const events = [
      createEvent({ type: 'error' }),
      createEvent({ id: 'e2', type: 'exception', sequence: 2 }),
      createEvent({ id: 'e3', type: 'tool_failed', sequence: 3 }),
    ];

    const timeline = projectRunTimeline(events);
    expect(timeline[0].type).toBe('error');
    expect(timeline[1].type).toBe('error');
    expect(timeline[2].type).toBe('error');
  });

  it('classifies run events correctly', () => {
    const events = [
      createEvent({ type: 'run_start' }),
      createEvent({ id: 'e2', type: 'run_complete', sequence: 2 }),
    ];

    const timeline = projectRunTimeline(events);
    expect(timeline).toHaveLength(1);
    expect(timeline[0].type).toBe('run');
    expect(timeline[0].durationMs).toBe(0);
  });

  it('defaults to note type for unknown events', () => {
    const events = [createEvent({ type: 'custom_event' })];

    const timeline = projectRunTimeline(events);
    expect(timeline[0].type).toBe('note');
  });

  it('extracts title from payload.name', () => {
    const events = [
      createEvent({ payload: { name: 'Web Search' } }),
    ];

    const timeline = projectRunTimeline(events);
    expect(timeline[0].title).toBe('Web Search');
  });

  it('extracts title from payload.toolName', () => {
    const events = [
      createEvent({ payload: { toolName: 'web_search' } }),
    ];

    const timeline = projectRunTimeline(events);
    expect(timeline[0].title).toBe('web_search');
  });

  it('generates title from event type when no name found', () => {
    const events = [createEvent({ type: 'tool_call' })];

    const timeline = projectRunTimeline(events);
    expect(timeline[0].title).toBe('Tool Call');
  });

  it('extracts status from payload', () => {
    const events = [
      createEvent({ payload: { status: 'running' } }),
    ];

    const timeline = projectRunTimeline(events);
    expect(timeline[0].status).toBe('running');
  });

  it('defaults to error status for error events', () => {
    const events = [createEvent({ type: 'error' })];

    const timeline = projectRunTimeline(events);
    expect(timeline[0].status).toBe('error');
  });

  it('defaults to ok status for non-error events', () => {
    const events = [createEvent({ type: 'llm_call' })];

    const timeline = projectRunTimeline(events);
    expect(timeline[0].status).toBe('ok');
  });

  it('extracts durationMs from payload', () => {
    const events = [
      createEvent({ payload: { durationMs: 500 } }),
    ];

    const timeline = projectRunTimeline(events);
    expect(timeline[0].durationMs).toBe(500);
  });

  it('extracts duration_ms from payload', () => {
    const events = [
      createEvent({ payload: { duration_ms: 300 } }),
    ];

    const timeline = projectRunTimeline(events);
    expect(timeline[0].durationMs).toBe(300);
  });

  it('returns null duration when not present', () => {
    const events = [createEvent()];

    const timeline = projectRunTimeline(events);
    expect(timeline[0].durationMs).toBeNull();
  });

  it('sets startedAt from event timestamp', () => {
    const events = [
      createEvent({ timestamp: '2024-01-01T12:00:00Z' }),
    ];

    const timeline = projectRunTimeline(events);
    expect(timeline[0].startedAt).toBe('2024-01-01T12:00:00Z');
  });

  it('includes event metadata in timeline item', () => {
    const events = [
      createEvent({
        metadata: { custom: 'value' },
        spanId: 'span-123',
      }),
    ];

    const timeline = projectRunTimeline(events);
    expect(timeline[0].metadata).toMatchObject({
      sequence: 1,
      spanId: 'span-123',
      eventType: 'llm_call',
      custom: 'value',
    });
  });

  it('generates id from index when event id is missing', () => {
    const events = [createEvent({ id: '' })];

    const timeline = projectRunTimeline(events);
    expect(timeline[0].id).toBe('event-0');
  });

  it('requires semantic compatibility in addition to spanId', () => {
    const start = createEvent({ type: 'tool_started' });
    const llmEnd = createEvent({ id: 'e2', type: 'llm_completed', sequence: 2 });

    expect(canPair(start, llmEnd)).toBe(false);
    expect(projectRunTimeline([start, llmEnd]).map((item) => item.type)).toEqual(['tool', 'llm']);
  });

  it('pairs failed events only with the matching operation kind', () => {
    const start = createEvent({ type: 'tool_started', timestamp: '2024-01-01T00:00:00Z' });
    const failed = createEvent({ id: 'e2', type: 'tool_failed', sequence: 2, timestamp: '2024-01-01T00:00:01Z' });

    const [item] = projectRunTimeline([start, failed]);
    expect(item.status).toBe('failed');
    expect(item.durationMs).toBe(1000);
  });

  it('does not fabricate duration for missing or reversed timestamps', () => {
    const missing = projectRunTimeline([
      createEvent({ type: 'llm_started', timestamp: null }),
      createEvent({ id: 'e2', type: 'llm_completed', sequence: 2, timestamp: '2024-01-01T00:00:01Z' }),
    ]);
    const reversed = projectRunTimeline([
      createEvent({ type: 'llm_started', timestamp: '2024-01-01T00:00:02Z' }),
      createEvent({ id: 'e2', type: 'llm_completed', sequence: 2, timestamp: '2024-01-01T00:00:01Z' }),
    ]);

    expect(missing[0].durationMs).toBeNull();
    expect(reversed[0].durationMs).toBeNull();
  });

  it('pairs events when the input is out of order', () => {
    const start = createEvent({ type: 'llm_started', sequence: 2, timestamp: '2024-01-01T00:00:00Z' });
    const end = createEvent({ id: 'e2', type: 'llm_completed', sequence: 1, timestamp: '2024-01-01T00:00:01Z' });

    const timeline = projectRunTimeline([start, end]);
    expect(timeline).toHaveLength(1);
    expect(timeline[0].durationMs).toBe(1000);
  });
});
