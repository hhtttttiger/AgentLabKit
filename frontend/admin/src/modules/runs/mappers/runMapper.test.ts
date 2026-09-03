/**
 * Run Mapper Tests
 */

import { describe, it, expect } from 'vitest';
import { mapRunSummary, mapRunDetail, mapRunEvent, mapRunCost, mapRunEvaluation } from './runMapper';
import type { RunSummaryDto, RunDetailDto, RunEventDto, RunCostDto, RunEvaluationDto } from '../api/dto';

describe('mapRunSummary', () => {
  it('maps a complete DTO', () => {
    const dto: RunSummaryDto = {
      id: '1',
      agentKey: 'test-agent',
      runId: 'run-123',
      agentVersion: 3,
      inputSummary: 'Hello',
      outputSummary: 'World',
      status: 'success',
      durationMs: 1500,
      tokenUsageJson: { totalTokens: 100, inputTokens: 60, outputTokens: 40 },
      errorMessage: null,
      createdAtUtc: '2024-01-15T10:30:00Z',
    };

    const result = mapRunSummary(dto);

    expect(result.id).toBe('run-123');
    expect(result.agentKey).toBe('test-agent');
    expect(result.agentVersion).toBe('3');
    expect(result.status).toBe('success');
    expect(result.durationMs).toBe(1500);
    expect(result.startedAt).toBe('2024-01-15T10:30:00Z');
    expect(result.completedAt).toBeNull();
  });

  it('normalizes completed status to success', () => {
    const dto: RunSummaryDto = {
      id: '1',
      agentKey: 'test-agent',
      runId: 'run-123',
      agentVersion: 1,
      inputSummary: null,
      outputSummary: null,
      status: 'completed',
      durationMs: null,
      tokenUsageJson: {},
      errorMessage: null,
      createdAtUtc: null,
    };

    const result = mapRunSummary(dto);
    expect(result.status).toBe('success');
  });

  it('normalizes error status to failed', () => {
    const dto: RunSummaryDto = {
      id: '1',
      agentKey: 'test-agent',
      runId: 'run-123',
      agentVersion: 1,
      inputSummary: null,
      outputSummary: null,
      status: 'error',
      durationMs: null,
      tokenUsageJson: {},
      errorMessage: 'Something went wrong',
      createdAtUtc: null,
    };

    const result = mapRunSummary(dto);
    expect(result.status).toBe('failed');
    expect(result.errorMessage).toBe('Something went wrong');
  });

  it('handles unknown status', () => {
    const dto: RunSummaryDto = {
      id: '1',
      agentKey: 'test-agent',
      runId: 'run-123',
      agentVersion: 1,
      inputSummary: null,
      outputSummary: null,
      status: 'something-unknown',
      durationMs: null,
      tokenUsageJson: {},
      errorMessage: null,
      createdAtUtc: null,
    };

    const result = mapRunSummary(dto);
    expect(result.status).toBe('unknown');
  });

  it('handles null/undefined fields gracefully', () => {
    const dto: RunSummaryDto = {
      id: '1',
      agentKey: 'test-agent',
      runId: 'run-123',
      agentVersion: null,
      inputSummary: null,
      outputSummary: null,
      status: 'success',
      durationMs: null,
      tokenUsageJson: {},
      errorMessage: null,
      createdAtUtc: null,
    };

    const result = mapRunSummary(dto);
    expect(result.agentVersion).toBeNull();
    expect(result.durationMs).toBeNull();
    expect(result.errorMessage).toBeNull();
  });
});

describe('mapRunDetail', () => {
  it('maps a complete DTO', () => {
    const dto: RunDetailDto = {
      id: '1',
      agentKey: 'test-agent',
      runId: 'run-123',
      agentVersion: 3,
      inputSummary: 'Hello',
      outputSummary: 'World',
      status: 'success',
      durationMs: 1500,
      tokenUsageJson: { totalTokens: 100, inputTokens: 60, outputTokens: 40 },
      errorMessage: null,
      createdAtUtc: '2024-01-15T10:30:00Z',
      toolCallsJson: [{ toolName: 'search' }],
    };

    const result = mapRunDetail(dto);

    expect(result.id).toBe('run-123');
    expect(result.input).toBe('Hello');
    expect(result.output).toBe('World');
    expect(result.totalTokens).toBe(100);
    expect(result.metadata.toolCallsCount).toBe(1);
  });
});

describe('mapRunEvent', () => {
  it('maps a complete DTO', () => {
    const dto: RunEventDto = {
      id: 'evt-1',
      sequence: 1,
      type: 'llm.call',
      timestamp: '2024-01-15T10:30:00Z',
      spanId: 'span-1',
      payload: { model: 'gpt-4' },
      metadata: { source: 'test' },
    };

    const result = mapRunEvent(dto);

    expect(result.id).toBe('evt-1');
    expect(result.sequence).toBe(1);
    expect(result.type).toBe('llm.call');
    expect(result.spanId).toBe('span-1');
  });

  it('handles missing optional fields', () => {
    const dto: RunEventDto = {
      id: 'evt-1',
      sequence: 0,
      type: 'unknown',
      timestamp: '2024-01-15T10:30:00Z',
      spanId: null,
      payload: {},
      metadata: {},
    };

    const result = mapRunEvent(dto);
    expect(result.spanId).toBeNull();
  });
});

describe('mapRunCost', () => {
  it('maps a complete DTO', () => {
    const dto: RunCostDto = {
      totalUsd: 0.05,
      inputTokens: 1000,
      outputTokens: 500,
      llmCalls: [
        { modelKey: 'gpt-4', costUsd: 0.03, inputTokens: 600, outputTokens: 300 },
        { modelKey: 'gpt-3.5-turbo', costUsd: 0.02, inputTokens: 400, outputTokens: 200 },
      ],
    };

    const result = mapRunCost(dto);

    expect(result.totalUsd).toBe(0.05);
    expect(result.inputTokens).toBe(1000);
    expect(result.outputTokens).toBe(500);
    expect(result.llmCalls).toHaveLength(2);
    expect(result.llmCalls[0].modelKey).toBe('gpt-4');
  });
});

describe('mapRunEvaluation', () => {
  it('maps a complete DTO', () => {
    const dto: RunEvaluationDto = {
      overallScore: 0.85,
      metrics: [
        { name: 'accuracy', score: 0.9 },
        { name: 'relevance', score: 0.8 },
      ],
    };

    const result = mapRunEvaluation(dto);

    expect(result.overallScore).toBe(0.85);
    expect(result.metrics).toHaveLength(2);
    expect(result.metrics[0].name).toBe('accuracy');
    expect(result.metrics[0].score).toBe(0.9);
  });

  it('handles null overallScore', () => {
    const dto: RunEvaluationDto = {
      overallScore: null,
      metrics: [],
    };

    const result = mapRunEvaluation(dto);
    expect(result.overallScore).toBeNull();
    expect(result.metrics).toHaveLength(0);
  });
});
