import { describe, expect, it } from 'vitest';
import { adminI18nResources } from './resources';

function collectLeafKeys(value: unknown, prefix = ''): string[] {
  if (value === null || typeof value !== 'object') return [prefix];
  return Object.entries(value as Record<string, unknown>)
    .flatMap(([key, child]) => collectLeafKeys(child, prefix ? `${prefix}.${key}` : key));
}

describe('adminI18nResources', () => {
  it('zh-CN and en-US both exist and have parity', () => {
    expect(adminI18nResources['zh-CN']).toBeDefined();
    expect(adminI18nResources['en-US']).toBeDefined();
    expect(collectLeafKeys(adminI18nResources['zh-CN']).sort())
      .toEqual(collectLeafKeys(adminI18nResources['en-US']).sort());
  });
});
