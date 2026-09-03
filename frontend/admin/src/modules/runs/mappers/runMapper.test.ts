import { describe, expect, it } from 'vitest';
import { mapRunDetail } from './runMapper';
import type { RunDetailDto } from '../api/dto';

const dto: RunDetailDto = {
  runId: 'run-authoritative', traceId: 'trace-1', status: 'completed', targetType: 'agent',
  targetKey: 'support', targetVersion: '3', input: 'hello', output: 'world',
  startedAt: '2026-01-01T00:00:00Z', completedAt: null, durationMs: 0, sessionId: null,
  errorCode: null, errorMessage: null, metadata: {},
};

describe('mapRunDetail', () => {
  it('preserves authoritative identities and missing timestamps', () => {
    const result = mapRunDetail(dto);
    expect(result.id).toBe('run-authoritative');
    expect(result.traceId).toBe('trace-1');
    expect(result.completedAt).toBeNull();
    expect(result.durationMs).toBe(0);
    expect(result.sessionId).toBeNull();
  });

  it('accepts only canonical lifecycle statuses', () => {
    expect(mapRunDetail({ ...dto, status: 'handoff' }).status).toBe('unknown');
    expect(mapRunDetail({ ...dto, status: 'cancelled' }).status).toBe('cancelled');
  });
});
