import { describe, expect, it } from 'vitest';
import { normalizeJsonText, validateJsonText } from './json';

describe('json helpers', () => {
  it('validates json object kind', () => {
    expect(validateJsonText('{"x":1}', 'object')).toBeNull();
    expect(validateJsonText('[]', 'object')).toBe('这里需要输入 JSON 对象。');
  });

  it('normalizes empty content to defaults', () => {
    expect(normalizeJsonText('', 'object')).toBe('{}');
    expect(normalizeJsonText('', 'array')).toBe('[]');
  });
});
