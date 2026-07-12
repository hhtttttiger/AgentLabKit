import { describe, expect, it } from 'vitest';
import { buildCardDisplayNameMap, toMonitoringOverview, toUsageSummaryView } from './mappers';

describe('model monitoring mappers', () => {
  it('maps card keys to display names and computes error rate', () => {
    const cardNames = buildCardDisplayNameMap([
      {
        modelKey: 'card.alpha',
        modelName: 'gpt-4.1-mini',
        displayName: '主模型',
        isEnabled: true,
      },
    ]);

    const summary = toUsageSummaryView(
      {
        modelKey: 'card.alpha',
        totalRequests: 40,
        successCount: 36,
        errorCount: 4,
        totalInputTokens: 1000,
        totalOutputTokens: 500,
        totalEstimatedCost: 0.12,
        avgDurationMs: 250,
        totalCacheWriteTokens: 0,
        totalCacheReadTokens: 0,
      },
      cardNames,
    );

    expect(summary.displayName).toBe('主模型');
    expect(summary.errorRate).toBe(0.1);
  });

  it('passes through pre-computed overview metrics from backend response', () => {
    const displayNames = new Map([['card.alpha', '主模型'], ['card.beta', '备用模型']]);

    const overview = toMonitoringOverview(
      {
        totalRequests: 40,
        totalTokens: 600,
        totalErrors: 4,
        averageLatencyMs: 350,
        modelSummaries: [
          {
            modelKey: 'card.alpha',
            totalRequests: 10,
            successCount: 9,
            errorCount: 1,
            totalInputTokens: 100,
            totalOutputTokens: 50,
            totalEstimatedCost: 0.01,
            avgDurationMs: 200,
            totalCacheWriteTokens: 0,
            totalCacheReadTokens: 0,
          },
          {
            modelKey: 'card.beta',
            totalRequests: 30,
            successCount: 27,
            errorCount: 3,
            totalInputTokens: 300,
            totalOutputTokens: 150,
            totalEstimatedCost: 0.03,
            avgDurationMs: 400,
            totalCacheWriteTokens: 0,
            totalCacheReadTokens: 0,
          },
        ],
      },
      displayNames,
    );

    expect(overview.totalRequests).toBe(40);
    expect(overview.totalTokens).toBe(600);
    expect(overview.totalErrors).toBe(4);
    expect(overview.averageLatencyMs).toBe(350);
    expect(overview.modelSummaries).toHaveLength(2);
    expect(overview.modelSummaries[0].displayName).toBe('主模型');
    expect(overview.modelSummaries[1].displayName).toBe('备用模型');
  });
});
