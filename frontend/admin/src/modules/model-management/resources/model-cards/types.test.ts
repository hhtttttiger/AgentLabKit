import { describe, expect, it } from 'vitest';
import { toModelQuery } from './types';

describe('toModelQuery', () => {
  it('serializes feature filters into backend query fields', () => {
    expect(
      toModelQuery({
        featureKey: 'function_call',
        featureIsSupported: 'true',
        featureValueJson: 'true',
        isEnabled: 'false',
        page: 2,
        pageSize: 25,
      }),
    ).toEqual({
      featureKey: 'function_call',
      featureIsSupported: true,
      featureValueJson: 'true',
      isEnabled: false,
      page: 2,
      pageSize: 25,
    });
  });
});
