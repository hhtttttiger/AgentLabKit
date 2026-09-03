import { describe, expect, it } from 'vitest';
import { formatResult } from './RunComparePage';

describe('formatResult', () => {
  it('preserves zero scores and tri-state verdicts', () => {
    expect(formatResult({ score: 0, passed: true })).toBe('0 / pass');
    expect(formatResult({ score: 0, passed: false })).toBe('0 / fail');
    expect(formatResult({ score: 0, passed: null })).toBe('0 / —');
  });

  it('renders unavailable comparison results explicitly', () => {
    expect(formatResult(null)).toBe('—');
    expect(formatResult({ score: null, passed: null })).toBe('— / —');
  });
});
