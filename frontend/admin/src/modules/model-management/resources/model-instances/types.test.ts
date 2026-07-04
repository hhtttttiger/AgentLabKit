import { describe, expect, it } from 'vitest';
import { toModelInstanceQuery } from './types';

describe('toModelInstanceQuery', () => {
  it('serializes feature filters into backend query fields', () => {
    expect(
      toModelInstanceQuery({
        modelKey: 'card.text',
        featureKey: 'reasoning',
        featureIsSupported: 'false',
        featureValueJson: '"advanced"',
        type: 'Text',
        isEnabled: 'true',
        isHealthy: 'false',
        page: 3,
        pageSize: 50,
      }),
    ).toEqual({
      modelKey: 'card.text',
      featureKey: 'reasoning',
      featureIsSupported: false,
      featureValueJson: '"advanced"',
      type: 'Text',
      isEnabled: true,
      isHealthy: false,
      page: 3,
      pageSize: 50,
    });
  });
});
