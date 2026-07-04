import { describe, expect, it } from 'vitest';
import { switchTestLanguage } from '@/shared/test/setup';
import { formatLatency } from './formatters';

describe('model monitoring formatters', () => {
  it('formats latency with locale-aware numeric portions', async () => {
    await switchTestLanguage('zh-CN');
    expect(formatLatency(999.4)).toBe(`${new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 0 }).format(999.4)} ms`);
    expect(formatLatency(12_345_678)).toBe(
      `${new Intl.NumberFormat('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(12_345_678 / 1000)} s`,
    );

    await switchTestLanguage('en-US');
    expect(formatLatency(999.4)).toBe(`${new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(999.4)} ms`);
    expect(formatLatency(12_345_678)).toBe(
      `${new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(12_345_678 / 1000)} s`,
    );
  });
});
